# EVA API — Guide développeur

**Version** : 0.3.0
**Phase** : 4(F) — R-042
**Base URL** : `http://127.0.0.1:8000`
**Docs interactives** : `http://127.0.0.1:8000/docs` (Swagger UI)

> **Usage local uniquement.** L'API écoute sur `127.0.0.1` — non exposée réseau.
> Exposition réseau (`0.0.0.0`) prévue en Phase 5 après validation du modèle auth.

---

## Sommaire

1. [Installation et lancement](#1-installation-et-lancement)
2. [Authentification](#2-authentification)
3. [Endpoints](#3-endpoints)
   - [GET /health](#get-health)
   - [GET /status](#get-status)
   - [POST /chat](#post-chat)
   - [GET /chat/stream](#get-chatstream)
4. [Rate Limiting](#4-rate-limiting)
5. [Codes d'erreur](#5-codes-derreur)
6. [Exemples complets](#6-exemples-complets)
7. [Non-goals Phase 4](#7-non-goals-phase-4)

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
#   API Key : a3f8c2d1e9b047...  ← clé à conserver
#   Docs  : http://127.0.0.1:8000/docs
#   Redoc : http://127.0.0.1:8000/redoc

# Via uvicorn directement
uvicorn eva.api.app:app --host 127.0.0.1 --port 8000
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

Tous les endpoints sauf `/health` exigent une clé API.

### Méthodes acceptées (par ordre de priorité)

| Méthode | Exemple | Usage |
|---|---|---|
| Header `Authorization` | `Authorization: Bearer <key>` | Standard — curl, SDK, client HTTP |
| Header `X-EVA-Key` | `X-EVA-Key: <key>` | Fallback pratique |
| Query param `?api_key=` | `?api_key=<key>` | EventSource navigateur (headers non supportés) |

### Exemples curl

```bash
KEY=$(eva --print-api-key)

# Header standard
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/status

# Header alternatif
curl -H "X-EVA-Key: $KEY" http://127.0.0.1:8000/status

# Query param (SSE uniquement — voir /chat/stream)
curl -N "http://127.0.0.1:8000/chat/stream?message=Bonjour&api_key=$KEY"
```

### Réponse sans clé / clé invalide

```json
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer

{
  "detail": "Clé API requise. Header : Authorization: Bearer <key>"
}
```

---

## 3. Endpoints

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

| Code | Description |
|---|---|
| 200 | Toujours — état inclus dans le corps |
| 401 | Clé API manquante ou invalide |

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

| Champ | Type | Requis | Description |
|---|---|---|---|
| `message` | `string` | Oui | Message envoyé à EVA (non vide) |
| `conversation_id` | `string` | Non | UUID de conversation — généré si absent |

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

| Champ | Type | Description |
|---|---|---|
| `response` | `string` | Réponse textuelle d'EVA |
| `conversation_id` | `string` | UUID à réutiliser pour la suite de la conversation |
| `metadata.provider` | `string` | Fournisseur LLM (`"ollama"`) |
| `metadata.latency_ms` | `int` | Latence de l'appel LLM en millisecondes |

#### Codes de réponse

| Code | Description |
|---|---|
| 200 | Réponse reçue |
| 401 | Clé API manquante ou invalide |
| 422 | Corps invalide (message vide, JSON malformé) |
| 429 | Rate limit dépassé — `Retry-After: 60` |
| 500 | Erreur interne du moteur EVA |
| 503 | Moteur EVA non démarré |

---

### GET /chat/stream

**Auth requise + Rate limited.**

Streaming SSE (Server-Sent Events) — retourne la réponse token par token.
Idéal pour une UX avec affichage progressif (web UI, terminal).

> **NOTE Phase 4(C)** : FAKE STREAM — `engine.process()` est bloquant.
> La réponse est découpée mot par mot avec un délai simulé de ~40 ms/mot.
> Phase 5 branchera le streaming natif Ollama.

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
data: {"latency_ms": 420, "ok": true}
```

En cas d'erreur moteur :

```
event: meta
data: {"conversation_id": "550e8400-...", "provider": "ollama"}

event: error
data: {"message": "Erreur lors du traitement."}
```

#### Paramètres query

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `message` | `string` | Oui | Message envoyé à EVA (1–2000 caractères) |
| `conversation_id` | `string` | Non | UUID de conversation — généré si absent |
| `api_key` | `string` | Non* | Clé API — alternative aux headers (EventSource) |

\* La clé doit être fournie via `?api_key=`, header `Authorization`, ou `X-EVA-Key`.

#### Authentification avec EventSource (navigateur)

L'API Web EventSource du navigateur ne supporte pas les headers customs.
La clé doit passer en query param :

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
  const { latency_ms } = JSON.parse(e.data);
  console.log(`\nLatence : ${latency_ms} ms`);
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

| Code | Description |
|---|---|
| 200 | Stream SSE ouvert (cf. `event: error` pour erreur moteur dans le stream) |
| 401 | Clé API manquante ou invalide |
| 429 | Rate limit dépassé — `Retry-After: 60` |
| 503 | Moteur EVA non démarré ou sécurité non initialisée |

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

| Code | Signification | Endpoints concernés |
|---|---|---|
| 200 | Succès (ou état dégradé pour `/status`) | Tous |
| 401 | Clé API manquante ou invalide | `/status`, `/chat`, `/chat/stream` |
| 422 | Corps de requête invalide (Pydantic) | `/chat` |
| 429 | Rate limit dépassé | `/chat`, `/chat/stream` |
| 500 | Erreur interne du moteur EVA | `/chat` |
| 503 | Moteur non démarré / sécurité non initialisée | `/chat`, `/chat/stream` |

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

## 7. Non-goals Phase 4

Ces fonctionnalités sont hors scope Phase 4 et prévues pour Phase 5+ :

| Feature | Raison du report |
|---|---|
| HTTPS / TLS | Localhost-only — TLS sans CA = overhead sans gain |
| Exposition `0.0.0.0` | Après validation complète du modèle auth (Phase 5) |
| Session / cookie httpOnly | Pas d'authentification multi-utilisateur Phase 4 |
| X-Forwarded-For (proxy trust) | Pas d'exposition réseau Phase 4 |
| Rate limit Redis / persistant | In-memory suffisant pour local-only |
| WebSocket | SSE couvre les besoins Phase 4 |
| Streaming natif Ollama | Phase 5 — remplacera le FAKE STREAM actuel |

---

*Documentation générée pour EVA Phase 4(F) — R-042*
*Dernière mise à jour : 2026-02-28*
