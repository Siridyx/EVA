# EVA API — Guide développeur

**Version** : 0.3.0
**Phase** : 6(D.1) — hardening multi-utilisateurs
**Base URL** : `http://127.0.0.1:8000`
**OpenAPI JSON** : `http://127.0.0.1:8000/openapi.json`

> **Usage local uniquement.** L'API écoute sur `127.0.0.1` — non exposée réseau.

> **Docs UI (`/docs`, `/redoc`) — développement uniquement.**
> Ces endpoints ne sont pas protégés par authentification.
> Ne pas exposer en production. La désactivation conditionnelle (mode `prod`)
> est planifiée en **Phase 6(C)**. Pour afficher les URLs dev localement :
> ```bash
> eva --print-api-urls
> ```

---

## Sommaire

1. [Installation et lancement](#1-installation-et-lancement)
2. [Authentification](#2-authentification)
3. [Endpoints](#3-endpoints)
   - [POST /auth/login](#post-authlogin)
   - [POST /auth/logout](#post-authlogout)
   - [POST /auth/register](#post-authregister)
   - [GET /me](#get-me)
   - [GET /health](#get-health)
   - [GET /status](#get-status)
   - [POST /chat](#post-chat)
   - [GET /chat/stream](#get-chatstream)
   - [GET /metrics](#get-metrics)
4. [Rate Limiting](#4-rate-limiting)
5. [Codes d'erreur](#5-codes-derreur)
6. [Exemples complets](#6-exemples-complets)
7. [Non-goals / Roadmap](#7-non-goals--roadmap)

---

## 1. Installation et lancement

### Prérequis

- Python ≥ 3.9, < 3.13
- Ollama installé et démarré (`ollama serve`)
- EVA installé avec l'extra `[api]`

### Installation

```bash
# Installation depuis le répertoire du projet
pip install -e ".[api]"

# Ou avec tous les extras
pip install -e ".[all]"
```

### Lancement

```bash
# Via CLI EVA (recommandé)
eva --api

# Sortie au démarrage :
# EVA API v0.3.0 — http://127.0.0.1:8000
#   API key : (set) -- run 'eva --print-api-key' to display
#   API     : http://127.0.0.1:8000
#   OpenAPI : http://127.0.0.1:8000/openapi.json
#   Note    : Docs UI (/docs) is for development only.

# Avec HTTPS (Phase 6(B))
eva --api --tls
# → https://127.0.0.1:8000 (certificat auto-signé dans eva/data/certs/)

# Via uvicorn directement
uvicorn eva.api.app:app --host 127.0.0.1 --port 8000

# Afficher toutes les URLs de dev (inclut /docs et /redoc)
eva --print-api-urls
```

### Récupérer la clé API

```bash
# Affiche (ou génère) la clé sans démarrer le serveur
eva --print-api-key
```

La clé est stockée dans `eva/data/secrets/api_key.txt` (256 bits, `chmod 600`).
Elle persiste entre les redémarrages.

---

## 2. Authentification

Tous les endpoints sauf `/health` et `/auth/logout` exigent une authentification.

### Méthode recommandée — Session Web UI (Phase 6(A))

1. `POST /auth/login` avec la clé API → reçoit cookie `eva_session` (HttpOnly, SameSite=Strict)
2. Toutes les requêtes suivantes utilisent le cookie automatiquement (navigateur)
3. `POST /auth/logout` pour révoquer la session

### Méthodes acceptées (par ordre de priorité)

| Méthode                 | Exemple                             | Usage                                                |
| ----------------------- | ----------------------------------- | ---------------------------------------------------- |
| Cookie `eva_session`    | Automatique (navigateur)            | Web UI — EventSource n'a pas besoin de `?api_key=`   |
| Header `Authorization`  | `Authorization: Bearer <key>`       | Standard — curl, SDK, client HTTP                    |
| Header `X-EVA-Key`      | `X-EVA-Key: <key>`                  | Fallback pratique                                    |
| Query param `?api_key=` | `?api_key=<key>`                    | Backward compat curl/SSE sans headers                |

### Exemples curl

```bash
KEY=$(eva --print-api-key)

# Session (recommandé pour web)
curl -c cookies.txt -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'"$KEY"'"}'
curl -b cookies.txt http://127.0.0.1:8000/status  # cookie envoyé automatiquement

# Header standard (scripts / API)
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/status

# Header alternatif
curl -H "X-EVA-Key: $KEY" http://127.0.0.1:8000/status

# Query param (SSE backward compat)
curl -N "http://127.0.0.1:8000/chat/stream?message=Bonjour&api_key=$KEY"
```

### Réponse sans clé / clé invalide

```json
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer

{
  "detail": "Cle API manquante ou invalide."
}
```

---

## 3. Endpoints

### POST /auth/login

**Public (pas d'auth requise) — Rate limited.**

Valide la clé API et crée une session. Le cookie `eva_session` est positionné automatiquement.
La session expire après 24h. Utiliser `POST /auth/logout` pour la révoquer explicitement.

#### Requête

```bash
KEY=$(eva --print-api-key)
curl -c cookies.txt -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "'"$KEY"'"}'
```

#### Corps de la requête

```json
{"api_key": "votre_cle_api"}
```

#### Réponse 200

```json
{"status": "ok"}
```

Header de réponse :
```
Set-Cookie: eva_session=<token>; HttpOnly; Path=/; SameSite=strict; Max-Age=86400
```

#### Codes de réponse

| Code | Description                        |
| ---- | ---------------------------------- |
| 200  | Session créée — cookie positionné  |
| 401  | Clé API invalide                   |
| 429  | Rate limit dépassé                 |
| 503  | Service non initialisé             |

---

### POST /auth/logout

**Public — aucune auth requise.**

Révoque la session active et supprime le cookie `eva_session`.

#### Requête

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/auth/logout
```

#### Réponse 200

```json
{"status": "ok"}
```

---

### POST /auth/register

**Auth requise (session admin) — Rate limited.**

Crée un nouveau compte utilisateur. Nécessite une session administrateur authentifiée.
La clé API seule (sans session) est refusée après le bootstrap du premier admin.

Pour créer le premier admin, utiliser `eva --create-admin` en ligne de commande.

#### Requête

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "motdepasse123", "role": "user"}'
```

#### Corps de la requête

```json
{
  "username": "alice",
  "password": "motdepasse123",
  "role": "user"
}
```

| Champ      | Type     | Requis | Description                        |
| ---------- | -------- | ------ | ---------------------------------- |
| `username` | `string` | Oui    | Nom d'utilisateur unique           |
| `password` | `string` | Oui    | Mot de passe (min 8 caractères)    |
| `role`     | `string` | Non    | `"user"` (défaut) ou `"admin"`     |

#### Codes de réponse

| Code | Description                                           |
| ---- | ----------------------------------------------------- |
| 200  | Compte créé                                           |
| 401  | Session admin requise (api-key seule refusée)         |
| 409  | Nom d'utilisateur déjà pris                           |
| 422  | Validation échouée (champs manquants, mot de passe)   |
| 429  | Rate limit dépassé                                    |

---

### GET /me

**Auth requise.**

Retourne les informations du compte authentifié (via cookie session ou Bearer).

#### Requête

```bash
curl -b cookies.txt http://127.0.0.1:8000/me
```

#### Réponse 200

```json
{
  "id": 1,
  "username": "admin",
  "role": "admin"
}
```

#### Codes de réponse

| Code | Description                     |
| ---- | ------------------------------- |
| 200  | Informations compte             |
| 401  | Non authentifié                 |

---

### GET /health

**Public — aucune auth requise.**

Retourne `200 OK` si l'API est démarrée, même en mode dégradé (Ollama non disponible).
Utile pour sonder la disponibilité avant toute interaction.

#### Requête

```bash
curl http://127.0.0.1:8000/health
```

#### Réponse 200

```json
{
  "status": "ok",
  "version": "0.3.0"
}
```

---

### GET /status

**Auth requise — toujours HTTP 200.**

Retourne l'état détaillé du moteur EVA et de ses composants.
`engine` vaut `"RUNNING"`, `"STOPPED"` ou `"UNAVAILABLE"`.

#### Requête

```bash
KEY=$(eva --print-api-key)
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/status
```

#### Réponse 200 — moteur démarré

```json
{
  "engine": "RUNNING",
  "provider": "ollama",
  "components": {
    "memory": true,
    "prompt": true,
    "llm": true,
    "conversation": true
  }
}
```

#### Réponse 200 — moteur non disponible

```json
{
  "engine": "UNAVAILABLE",
  "provider": null,
  "components": {}
}
```

#### Codes de réponse

| Code | Description                          |
| ---- | ------------------------------------ |
| 200  | Toujours — état inclus dans le corps |
| 401  | Clé API manquante ou invalide        |

---

### POST /chat

**Auth requise + Rate limited.**

Envoie un message à EVA et reçoit la réponse complète en JSON.
Bloquant jusqu'à la réponse complète du LLM (~1–5 s selon le modèle).

Préférez `GET /chat/stream` pour afficher les tokens progressivement.

#### Requête

```bash
KEY=$(eva --print-api-key)
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Qui es-tu ?"}'
```

#### Corps de la requête

```json
{
  "message": "Qui es-tu ?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Champ             | Type     | Requis | Description                             |
| ----------------- | -------- | ------ | --------------------------------------- |
| `message`         | `string` | Oui    | Message envoyé à EVA (non vide)         |
| `conversation_id` | `string` | Non    | UUID de conversation — généré si absent |

#### Réponse 200

```json
{
  "response": "Bonjour ! Je suis EVA, votre assistant IA. Comment puis-je vous aider ?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "provider": "ollama",
    "latency_ms": 1240
  }
}
```

| Champ                 | Type     | Description                                        |
| --------------------- | -------- | -------------------------------------------------- |
| `response`            | `string` | Réponse textuelle d'EVA                            |
| `conversation_id`     | `string` | UUID à réutiliser pour la suite de la conversation |
| `metadata.provider`   | `string` | Fournisseur LLM (`"ollama"`)                       |
| `metadata.latency_ms` | `int`    | Latence de l'appel LLM en millisecondes            |

#### Codes de réponse

| Code | Description                                  |
| ---- | -------------------------------------------- |
| 200  | Réponse reçue                                |
| 401  | Clé API manquante ou invalide                |
| 422  | Corps invalide (message vide, JSON malformé) |
| 429  | Rate limit dépassé — `Retry-After: 60`       |
| 500  | Erreur interne du moteur EVA                 |
| 503  | Moteur EVA non démarré                       |

---

### GET /chat/stream

**Auth requise + Rate limited.**

Streaming SSE (Server-Sent Events) — retourne la réponse token par token.
Idéal pour une UX avec affichage progressif (web UI, terminal).

> **Phase 5(A)** : streaming natif Ollama via `process_stream()` —
> bridge `asyncio.Queue` + `asyncio.to_thread` (NDJSON Ollama → SSE).
> Le FAKE STREAM Phase 4 est remplacé.

#### Protocole SSE

Le serveur émet une séquence d'événements :

```
event: meta
data: {"conversation_id": "550e8400-...", "provider": "ollama"}

event: token
data: {"text": "Bonjour"}

event: token
data: {"text": " !"}

event: token
data: {"text": " Je"}

... (N événements token)

event: done
data: {"latency_ms": 420, "ok": true, "ttft_ms": 180, "tokens": 47, "tokens_per_sec": 12.3}
```

Le payload `event:done` contient toujours `latency_ms` et `ok`.
Les champs `ttft_ms`, `tokens` et `tokens_per_sec` sont présents si des tokens ont été émis.

En cas d'erreur moteur :

```
event: meta
data: {"conversation_id": "550e8400-...", "provider": "ollama"}

event: error
data: {"message": "Erreur lors du traitement."}
```

#### Paramètres query

| Paramètre         | Type     | Requis | Description                                     |
| ----------------- | -------- | ------ | ----------------------------------------------- |
| `message`         | `string` | Oui    | Message envoyé à EVA (1–2000 caractères)        |
| `conversation_id` | `string` | Non    | UUID de conversation — généré si absent         |
| `api_key`         | `string` | Non\*  | Clé API — alternative aux headers (EventSource) |

\* La clé doit être fournie via `?api_key=`, header `Authorization`, ou `X-EVA-Key`.

#### Authentification avec EventSource (navigateur)

**Phase 6(A) — méthode recommandée** : après `POST /auth/login`, le cookie `eva_session`
est envoyé automatiquement par le navigateur avec chaque requête EventSource.
Aucun `?api_key=` n'est nécessaire :

```javascript
// Après login (cookie eva_session positionné)
const params = new URLSearchParams({ message: "Bonjour EVA" });
const es = new EventSource(`/chat/stream?${params}`);
// Le cookie est envoyé automatiquement par le navigateur
```

**Backward compat — query param** (curl, clients sans cookies) :

```javascript
const API_KEY = "votre_clé_ici";
const params = new URLSearchParams({
  message: "Bonjour EVA",
  api_key: API_KEY,
});
const es = new EventSource(`/chat/stream?${params}`);

es.addEventListener("meta", (e) => {
  const { conversation_id } = JSON.parse(e.data);
  console.log("Conv ID:", conversation_id);
});

es.addEventListener("token", (e) => {
  const { text } = JSON.parse(e.data);
  process.stdout.write(text); // affichage progressif
});

es.addEventListener("done", (e) => {
  const { latency_ms, ttft_ms, tokens, tokens_per_sec } = JSON.parse(e.data);
  console.log(`\nLatence : ${latency_ms} ms`);
  if (ttft_ms !== undefined) console.log(`TTFT : ${ttft_ms} ms`);
  if (tokens_per_sec !== undefined)
    console.log(`Debit : ${tokens_per_sec} t/s`);
  es.close(); // IMPORTANT : fermer le stream
});

es.addEventListener("error", (e) => {
  if (e.data) {
    const { message } = JSON.parse(e.data);
    console.error("Erreur EVA:", message);
  } else {
    console.error("Connexion perdue");
  }
  es.close();
});
```

#### Exemple curl SSE

```bash
KEY=$(eva --print-api-key)

# -N désactive le buffering curl (affichage immédiat)
curl -N \
  -H "Authorization: Bearer $KEY" \
  "http://127.0.0.1:8000/chat/stream?message=Raconte-moi+une+blague"

# Sortie :
# event: meta
# data: {"conversation_id": "550e8400-e29b-41d4-a716-446655440000", "provider": "ollama"}
#
# event: token
# data: {"text": "Pourquoi"}
#
# event: token
# data: {"text": " les"}
# ...
# event: done
# data: {"latency_ms": 1840, "ok": true}
```

#### Headers de réponse

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

#### Codes de réponse

| Code | Description                                                              |
| ---- | ------------------------------------------------------------------------ |
| 200  | Stream SSE ouvert (cf. `event: error` pour erreur moteur dans le stream) |
| 401  | Clé API manquante ou invalide                                            |
| 429  | Rate limit dépassé — `Retry-After: 60`                                   |
| 503  | Moteur EVA non démarré ou sécurité non initialisée                       |

---

### GET /metrics

**Auth requise — Phase 5(C).**

Retourne les métriques de performance de l'API en mémoire : p50/p95 par endpoint,
TTFT (time-to-first-token) et débit token pour `/chat/stream`.
Ring buffer des 100 dernières requêtes. Aucune persistance disque.

#### Requête

```bash
KEY=$(eva --print-api-key)
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/metrics
```

#### Réponse 200

```json
{
  "uptime_s": 3600,
  "endpoints": {
    "chat": {
      "requests": 42,
      "errors": 1,
      "p50_ms": 1240,
      "p95_ms": 3810,
      "last_latency_ms": 1180
    },
    "chat_stream": {
      "requests": 18,
      "errors": 0,
      "p50_ms": 1320,
      "p95_ms": 3920,
      "p50_ttft_ms": 180,
      "p95_ttft_ms": 420,
      "last_latency_ms": 1300,
      "last_ttft_ms": 175,
      "last_token_count": 47,
      "last_tokens_per_sec": 12.3
    }
  }
}
```

| Champ                                       | Type          | Description                                        |
| ------------------------------------------- | ------------- | -------------------------------------------------- |
| `uptime_s`                                  | `int`         | Secondes depuis le démarrage du collecteur         |
| `endpoints.chat.requests`                   | `int`         | Nombre total de requêtes POST /chat (ring buf 100) |
| `endpoints.chat.errors`                     | `int`         | Nombre d'erreurs (ok=False)                        |
| `endpoints.chat.p50_ms`                     | `int`         | Percentile 50 des latences en ms                   |
| `endpoints.chat.p95_ms`                     | `int`         | Percentile 95 des latences en ms                   |
| `endpoints.chat_stream.p50_ttft_ms`         | `int`         | Percentile 50 du TTFT en ms                        |
| `endpoints.chat_stream.last_tokens_per_sec` | `float\|null` | Débit du dernier stream (tokens/s)                 |

#### Codes de réponse

| Code | Description                                        |
| ---- | -------------------------------------------------- |
| 200  | Métriques disponibles                              |
| 401  | Clé API manquante ou invalide                      |
| 503  | Collecteur non initialisé (moteur EVA non démarré) |

---

## 4. Rate Limiting

- **Algorithme** : fenêtre glissante de 60 secondes par IP
- **Limite par défaut** : 60 requêtes/minute
- **Configurable** via `api.rate_limit_per_min` dans `config.yaml`
- **Endpoints concernés** : `POST /chat` et `GET /chat/stream`
- **En cas de dépassement** : HTTP 429 + header `Retry-After: 60`

```bash
# config.yaml
api:
  rate_limit_per_min: 60  # ajuster selon les besoins
```

### Réponse 429

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "detail": "Trop de requêtes. Limite : 60 req/min."
}
```

---

## 5. Codes d'erreur

| Code | Signification                                  | Endpoints concernés                            |
| ---- | ---------------------------------------------- | ---------------------------------------------- |
| 200  | Succès (ou état dégradé pour `/status`)        | Tous                                           |
| 401  | Clé API manquante ou invalide                  | `/status`, `/chat`, `/chat/stream`, `/metrics` |
| 422  | Corps de requête invalide (Pydantic)           | `/chat`                                        |
| 429  | Rate limit dépassé                             | `/chat`, `/chat/stream`                        |
| 500  | Erreur interne du moteur EVA                   | `/chat`                                        |
| 503  | Moteur non démarré / collecteur non initialisé | `/chat`, `/chat/stream`, `/metrics`            |

### Format des erreurs

Toutes les erreurs suivent le format FastAPI standard :

```json
{
  "detail": "Message d'erreur lisible."
}
```

Pour les erreurs 422 (validation Pydantic) :

```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "Le message ne peut pas être vide.",
      "type": "value_error"
    }
  ]
}
```

> **Sécurité** : les erreurs 500 ne leakent aucune information interne
> (chemins fichiers, noms modèles, messages réseau). Cf. audit R-043, findings F-04/F-05.

---

## 6. Exemples complets

### Session de conversation multi-tours (curl)

```bash
KEY=$(eva --print-api-key)
BASE="http://127.0.0.1:8000"
AUTH="-H 'Authorization: Bearer $KEY'"

# Tour 1 — premier message
RESPONSE=$(curl -s -X POST "$BASE/chat" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour ! Comment tu t'\''appelles ?"}')

echo $RESPONSE | python3 -m json.tool

# Extraire le conversation_id pour le tour suivant
CONV_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])")

# Tour 2 — continuation de la conversation
curl -s -X POST "$BASE/chat" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Que peux-tu faire ?\", \"conversation_id\": \"$CONV_ID\"}" \
  | python3 -m json.tool
```

### Client Python simple

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# Récupérer la clé (en pratique : lire eva/data/secrets/api_key.txt)
import subprocess
api_key = subprocess.check_output(["eva", "--print-api-key"]).decode().strip()

headers = {"Authorization": f"Bearer {api_key}"}

# Vérifier l'état
status = requests.get(f"{BASE_URL}/status", headers=headers).json()
if status["engine"] != "RUNNING":
    raise RuntimeError("Moteur EVA non démarré")

# Envoyer un message
response = requests.post(
    f"{BASE_URL}/chat",
    headers=headers,
    json={"message": "Bonjour EVA !"},
)
data = response.json()
print(data["response"])
print(f"Latence : {data['metadata']['latency_ms']} ms")
```

### Streaming SSE avec sseclient-py

```python
import sseclient
import requests
import json

BASE_URL = "http://127.0.0.1:8000"
api_key = "votre_clé_ici"

response = requests.get(
    f"{BASE_URL}/chat/stream",
    headers={"Authorization": f"Bearer {api_key}"},
    params={"message": "Raconte-moi une histoire courte"},
    stream=True,
)
response.raise_for_status()

client = sseclient.SSEClient(response)
full_text = ""

for event in client.events():
    if event.event == "meta":
        data = json.loads(event.data)
        print(f"Conv ID : {data['conversation_id']}")
    elif event.event == "token":
        data = json.loads(event.data)
        print(data["text"], end="", flush=True)
        full_text += data["text"]
    elif event.event == "done":
        data = json.loads(event.data)
        print(f"\n\nLatence : {data['latency_ms']} ms")
        break
    elif event.event == "error":
        data = json.loads(event.data)
        print(f"\nErreur : {data['message']}")
        break
```

---

## 7. Non-goals / Roadmap

| Feature                         | Statut                                                     |
| ------------------------------- | ---------------------------------------------------------- |
| HTTPS / TLS                     | ✅ DONE Phase 6(B) — `eva --api --tls`                     |
| Session / cookie httpOnly       | ✅ DONE Phase 6(A) — `SessionManager`, login overlay       |
| Multi-utilisateurs              | ✅ DONE Phase 6(D) — UserStore SQLite, PBKDF2              |
| Rate limit auth endpoints       | ✅ DONE Phase 6(D.1)                                       |
| Isolation conversations         | ✅ DONE Phase 6(D.1) — `_resolve_conv_id()` namespacing    |
| Streaming natif Ollama          | ✅ DONE Phase 5(A) — `process_stream()`, bridge Queue      |
| Métriques temps réel            | ✅ DONE Phase 5(C) — `GET /metrics`                        |
| Exposition `0.0.0.0`            | ⏳ Phase 6(C) — avec CORS configurable + TLS               |
| Désactivation Swagger prod      | ⏳ Phase 6(C)                                              |
| X-Forwarded-For (proxy trust)   | ⏳ Phase 6(C) — après exposition réseau                    |
| Rate limit Redis / persistant   | Non prioritaire (local-only suffisant)                     |
| WebSocket                       | Non prioritaire (SSE couvre les besoins)                   |

---

_Documentation générée pour EVA Phase 6(D.1)_
_Dernière mise à jour : 2026-03-01_
