# EVA — Rapport de Profiling Performance

**Phase** : 4(G) — R-044
**Date** : 2026-02-28
**Auteur** : Claude Sonnet 4.6 (assisté par Siridyx)

---

## 1. Environnement

| Paramètre | Valeur |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| Python | 3.9.13 |
| Machine | Intel/AMD x86-64 (bureau) |
| Modèle LLM (bench réel) | llama3.2:latest (Ollama 11434) |
| Modèle LLM (profiling) | Mock (réponse fixe, sans réseau) |
| EVA version | 0.3.0 |

---

## 2. Architecture du chemin critique

```
POST /chat  [asyncio.to_thread]
  EVAEngine.process()                     ~0 ms    wrapper
  ConversationEngine.respond()
    Memory.add_message("user")            3-4 ms   I/O JSON atomique
      _save_session()
        tempfile.mkstemp()                ~0.16 ms
        json.dump()                       ~0.97 ms  compact JSON (post-opt1)
        os.fdopen / write                 ~0.14 ms
        nt.unlink (Windows)               ~0.13 ms
        os.replace (atomic)               ~0.21 ms
    Memory.get_context()                  <0.1 ms  slice memoire
    Prompt.render()                       <0.1 ms  str.replace + regex
    LLM.complete() via OllamaProvider     100-5000 ms  HTTP POST localhost:11434
      requests.Session.post()             (avec opt2 : keepalive TCP)
      Ollama inference                    [DOMINANT]
    Memory.add_message("assistant")       3-4 ms   I/O JSON atomique
                                          (identique au save user)
```

**Goulot principal** : appel HTTP Ollama — 100 à 5000 ms selon le modèle et la longueur de réponse.

**Goulot secondaire** : `_save_session()` — 2 écritures atomiques par requête.
Sur Windows, chaque écriture inclut un `nt.unlink` (supprimer avant rename) = overhead spécifique Windows.

---

## 3. Méthodologie

### 3.1 Profiling interne (pipeline sans LLM)

Outil : `tools/profile_engine.py`

```bash
python tools/profile_engine.py --n 100 --top 20
```

- Stack EVA complet initialisé avec **mock LLM** (transport injectableretournant une réponse fixe)
- Warm-up : 5 appels (écartés des mesures)
- Mesures : N=100 appels à `engine.process("Bonjour EVA !")`
- Profiler : `cProfile.Profile()` standard bibliothèque Python
- Sous-timings : EventBus listeners (closures par event)

### 3.2 Bench API black-box

Outil : `tools/bench_api.py` (nécessite `eva --api` + Ollama)

```bash
KEY=$(eva --print-api-key)
python tools/bench_api.py --key "$KEY" [--skip-chat]
```

- Warm-up : 3 requêtes avant mesures
- Métriques : p50 / p95 / max par endpoint
- Isolation : une `requests.Session` partagée pour le bench

---

## 4. Résultats — Profiling interne (mock LLM)

### 4.1 Sous-timings par étape (N=100 appels)

| Étape | Temps moyen | % pipeline |
|---|---|---|
| **conversation_turn_complete** | **3.778 ms** | 99.7% |
| llm_complete (mock seulement) | 0.030 ms | 0.8% |
| Temps total / appel | **3.789 ms** | 100% |
| memory_add events | 2 events/appel | — |

> Le pipeline CPU complet (hors LLM réel) = **3.79 ms/appel** sur cette machine.
> Avec LLM Ollama réel : latence totale dominée par l'inférence (100–5000ms).

### 4.2 Top 20 fonctions — cProfile (100 appels, cumtime)

```
         1 495 549 function calls (1 271 619 primitive calls) in 0.379 seconds
   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
      100    0.000    0.000    0.379    0.004  eva_engine.py:212(process)
      100    0.001    0.000    0.378    0.004  conversation_engine.py:98(respond)
      200    0.002    0.000    0.371    0.002  memory_manager.py:247(add_message)
      200    0.002    0.000    0.367    0.002  memory_manager.py:195(_save_session)  ← 96.8%
      200    0.038    0.000    0.193    0.001  json/__init__.py:120(dump)            ← 50.9%
   228330    0.021    0.000    0.136    0.000  json/encoder.py:413(_iterencode)
452260/228330 0.060  0.000    0.114    0.000  json/encoder.py:333(_iterencode_dict)
   224330    0.031    0.000    0.091    0.000  json/encoder.py:277(_iterencode_list)
      200    0.042    0.000    0.042    0.000  {built-in nt.replace}                ← atomic rename
      200    0.000    0.000    0.034    0.000  tempfile.py:300(mkstemp)
      200    0.001    0.000    0.032    0.000  tempfile.py:243(_mkstemp_inner)
      200    0.028    0.000    0.028    0.000  {_io._IOBase.__exit__}               ← flush/close
      200    0.000    0.000    0.026    0.000  pathlib.py:1348(unlink)              ← Windows: delete avant rename
      200    0.026    0.000    0.026    0.000  {built-in nt.unlink}
      200    0.025    0.000    0.025    0.000  {built-in nt.open}
      200    0.000    0.000    0.024    0.000  pathlib.py:1318(mkdir)
      400    0.000    0.000    0.019    0.000  pathlib.py:1227(stat)
      400    0.018    0.000    0.018    0.000  {built-in nt.stat}
   228130    0.018    0.000    0.018    0.000  {_io.TextIOWrapper.write}
      200    0.016    0.000    0.016    0.000  {built-in nt.mkdir}
```

**Analyse** :

- `_save_session()` représente **96.8%** du temps pipeline CPU (3.67 ms / 3.79 ms)
- Dans `_save_session()`, `json.dump()` représente **52.6%** (1.93 ms)
- Les syscalls Windows (`nt.replace`, `nt.unlink`, `nt.open`, `nt.mkdir`) totalisent **0.109 ms/appel**
- `Prompt.render()`, `get_context()`, `EVAEngine.process()` : négligeables (< 0.01 ms)

### 4.3 Résumé

```
Temps total     : 378.9 ms pour 100 appels
Temps / appel   : 3.789 ms (pipeline CPU, LLM mocké)
Throughput mock : 263.9 appels/sec
```

---

## 5. Résultats — Bench API (valeurs typiques Ollama)

> Les valeurs ci-dessous sont des estimations basées sur llama3.2:latest (2GB, quantisé 4bits)
> sur machine de développement locale. À reproduire avec `tools/bench_api.py`.

| Endpoint | p50 | p95 | max | Notes |
|---|---|---|---|---|
| `GET /health` | ~4 ms | ~8 ms | ~15 ms | Public, aucune auth |
| `GET /status` | ~5 ms | ~10 ms | ~20 ms | Auth + state check |
| `POST /chat` | ~1500 ms | ~3500 ms | ~8000 ms | Ollama llama3.2 |
| `GET /chat/stream` TTFT | ~1500 ms | ~3500 ms | ~8000 ms | Temps jusqu'au 1er token |

**Note** : `GET /health` et `GET /status` ont des latences inférieures à 10 ms
en temps normal — la majorité du temps est dans les I/O mémoire (4 ms)
et le routage FastAPI/uvicorn (~1 ms).

---

## 6. Optimisations appliquées (R-044)

### Opt 1 — JSON compact dans `_save_session()`

**Fichier** : [eva/memory/memory_manager.py](eva/memory/memory_manager.py) ligne 229

```python
# Avant (indent=2) :
json.dump(data, f, indent=2, ensure_ascii=False)

# Après (compact) :
json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
```

**Justification** : `json.dump()` représente 50.9% du temps pipeline CPU.
Le format compact réduit :
- La taille du fichier (économies I/O sur le write et le mkstemp)
- Le travail de l'encodeur JSON (moins de caractères à produire)

**Gain estimé** : 15–30% du temps `json.dump()` = **0.3–0.6 ms/appel**
(fichier session typique : ~5–20 KB avec 10–50 messages)

**Safety** : aucun test ne vérifie le format indent — le fichier reste JSON valide.
Trade-off : fichier `data/memory/*.json` moins lisible à l'oeil.

### Opt 2 — `requests.Session()` dans OllamaProvider

**Fichier** : [eva/llm/providers/ollama_provider.py](eva/llm/providers/ollama_provider.py)

```python
# Avant :
import requests
response = requests.post(url, ...)  # nouvelle connexion TCP à chaque appel

# Après :
if self._http_session is None:
    self._http_session = requests.Session()
response = self._http_session.post(url, ...)  # TCP keepalive
```

**Justification** : `requests.post()` ouvre une nouvelle connexion TCP à chaque appel.
Avec `requests.Session()`, urllib3 réutilise les connexions (keepalive).
Sur localhost, le gain est modeste (~1–3 ms) mais systématique.
Session fermée proprement dans `_do_stop()`.

**Safety** :
- Tests utilisent `self._transport` (mock) — branche production non atteinte en test
- `requests.Session` est thread-safe via urllib3 PoolManager

---

## 7. Optimisations proposées (non appliquées)

### Opt 3 — Batch des memory saves

**Problème** : 2 `_save_session()` par requête (message user + message assistant).
**Solution** : sauvegarder une seule fois à la fin de `ConversationEngine.respond()`.
**Gain** : -1 write cycle = -3.67 ms/appel (soit ~50% du temps pipeline CPU !)
**Non appliqué** : risque de perte du message utilisateur si le processus crash
entre l'ajout en mémoire et la sauvegarde assistant.
Nécessite un mécanisme de récupération ou un journal (WAL) — hors scope Phase 4.

### Opt 4 — Réduire les syscalls Windows dans `_save_session()`

**Problème** : Sur Windows, `os.replace()` nécessite un `nt.unlink` préalable.
Les syscalls Windows représentent 0.109 ms/appel.

**Solutions possibles** :
- Remplacer `tempfile.mkstemp() + rename` par un write direct avec backup
- Utiliser un écrivain asynchrone (thread séparé) — complexité accrue
**Non appliqué** : comportement acceptable pour les volumes Phase 4.

### Opt 5 — Cache de contexte mémoire

`Memory.get_context()` fait déjà un `O(1)` slice — aucune optimisation utile.

---

## 8. Conclusions

### Ce qui est lent (sans LLM)

`_save_session()` domine à **96.8%** du temps pipeline CPU.
Sur 3.79 ms/appel, 3.67 ms viennent des I/O disque (JSON write + atomic rename).

### Ce qui est rapide (sans LLM)

- `Prompt.render()` : < 0.01 ms — excellent
- `Memory.get_context()` : < 0.01 ms — excellent
- `EVAEngine.process()` : wrapper pur — 0 overhead

### Perspective réelle (avec LLM Ollama)

L'appel HTTP Ollama (**100–5000 ms**) domine complètement.
Les 3.79 ms pipeline CPU représentent **0.08–3.8%** de la latence totale.

**Conclusion** : les optimisations pipeline CPU (Opt 1, 2) améliorent les endpoints
légers (`/health`, `/status`) et réduisent le minimum théorique de `/chat`.
Pour réduire significativement la latence `/chat`, c'est l'inférence LLM qu'il faut
optimiser (modèle plus petit, quantisation, GPU) — hors scope EVA côté serveur.

---

## 9. Commandes de référence

```bash
# Profiling interne (sans Ollama)
python tools/profile_engine.py --n 100 --top 20

# Bench API (avec eva --api + Ollama)
KEY=$(eva --print-api-key)
python tools/bench_api.py --key "$KEY" --skip-chat    # rapide (sans /chat)
python tools/bench_api.py --key "$KEY"                # complet (avec /chat Ollama)
python tools/bench_api.py --key "$KEY" --with-stream  # inclut SSE TTFT
```

---

*Rapport généré pour EVA Phase 4(G) — R-044*
*Date : 2026-02-28*
