"""
EVA API REST — Application FastAPI (R-031).

Scope Phase 3 :
    POST /chat   — envoyer un message, recevoir la réponse structurée
    GET  /status — état du moteur (toujours 200)
    GET  /health — healthcheck (toujours 200, public)

Phase 4(B) :
    Auth : Authorization: Bearer <key> ou X-EVA-Key: <key>
    /health : public (toujours 200, aucune auth)
    /status : protégé (401 sans clé valide)
    /chat   : protégé + rate limited (401 sans clé, 429 si > 60 req/min)

Phase 4(C) :
    GET /chat/stream : SSE streaming (auth + rate limit)
    FAKE STREAM : engine.process() → split mots + délai simulé
    Phase 5 branchera le streaming natif OllamaProvider.

Future phases :
    - Streaming natif provider (Phase 5)
    - Exposition 0.0.0.0 (Phase 5, après validation auth)
    - WebSocket (Phase 5)

Lancement :
    eva --api                       # via CLI
    uvicorn eva.api.app:app         # via uvicorn directement

Docs auto : http://localhost:8000/docs

Standards :
- Python 3.9 strict
- PEP8 strict
- asyncio.to_thread() pour appels LLM synchrones
- HTTPException pour les erreurs HTTP
- /status toujours 200 (mode dégradé inclus)
- host=127.0.0.1 strict (Phase 4 — auth ajoutée, exposition Phase 5)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, field_validator

from eva import __version__
from eva.api.metrics import MetricsCollector
from eva.api.security import ApiKeyManager, RateLimiter, SessionManager
from eva.api.users import User, UserRole, UserStore
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.core.eva_engine import EVAEngine
from eva.ui.command_registry import CommandContext
from eva.ui.commands import make_default_registry


# ---------------------------------------------------------------------------
# Schémas Pydantic — contrat R-031 LOCKED (inchangé Phase 4(B))
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Corps de la requête POST /chat."""

    message: str
    conversation_id: Optional[str] = None  # fourni par le client ou généré

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le message ne peut pas être vide.")
        return v


class ChatMetadata(BaseModel):
    """Métadonnées de la réponse POST /chat."""

    provider: str
    latency_ms: int


class ChatResponse(BaseModel):
    """Réponse de POST /chat."""

    response: str
    conversation_id: str
    metadata: ChatMetadata


class StatusResponse(BaseModel):
    """
    Réponse de GET /status.

    Toujours HTTP 200 — même si le moteur n'est pas démarré.
    `engine` vaut "RUNNING", "STOPPED" ou "UNAVAILABLE".
    """

    engine: str  # "RUNNING" | "STOPPED" | "UNAVAILABLE"
    provider: Optional[str]
    components: Dict[str, bool]


class HealthResponse(BaseModel):
    """Réponse de GET /health."""

    status: str
    version: str


# ---------------------------------------------------------------------------
# État partagé (module-level, initialisé au lifespan)
# ---------------------------------------------------------------------------


@dataclass
class EvaState:
    """
    État partagé de l'API EVA.

    Initialisé une seule fois au démarrage via lifespan().
    Accessible globalement via `_state`.
    """

    engine: Optional[EVAEngine] = None
    config: Optional[ConfigManager] = None
    event_bus: Optional[EventBus] = None
    registry: Optional[Any] = None  # CommandRegistry
    ctx: Optional[CommandContext] = None
    init_error: Optional[str] = None   # Erreur d'init partielle
    key_manager: Optional[ApiKeyManager] = None   # Phase 4(B) — auth
    rate_limiter: Optional[RateLimiter] = None    # Phase 4(B) — rate limit
    metrics_collector: Optional[MetricsCollector] = None  # Phase 5(C) — observabilite
    session_manager: Optional[SessionManager] = None  # Phase 6(A) — session cookie auth
    tls: bool = False                             # Phase 6(B) — HTTPS mode
    user_store: Optional[UserStore] = None        # Phase 6(D) — multi-utilisateurs


_state = EvaState()


# ---------------------------------------------------------------------------
# Initialisation EVA (synchrone — appelée depuis asyncio.to_thread)
# ---------------------------------------------------------------------------


def _init_eva() -> None:
    """
    Initialise tous les composants EVA.

    Même séquence que repl.py / tui/app.py.
    Erreurs non-bloquantes : l'API reste utilisable en mode dégradé.
    """
    try:
        _state.config = ConfigManager()
        _state.event_bus = EventBus()

        from eva.memory.memory_manager import MemoryManager

        memory = MemoryManager(_state.config, _state.event_bus)
        memory.start()

        from eva.prompt.prompt_manager import PromptManager

        prompt = PromptManager(_state.config, _state.event_bus)
        prompt.start()

        from eva.llm.providers.ollama_provider import OllamaProvider

        llm = OllamaProvider(_state.config, _state.event_bus)
        llm.start()

        from eva.conversation.conversation_engine import ConversationEngine

        conv = ConversationEngine(
            _state.config, _state.event_bus, memory, prompt, llm
        )
        conv.start()

        _state.engine = EVAEngine(_state.config, _state.event_bus)
        _state.engine.set_conversation_engine(conv)

        _state.registry = make_default_registry()
        _state.ctx = CommandContext(
            engine=_state.engine,
            config=_state.config,
            event_bus=_state.event_bus,
            registry=_state.registry,
        )

    except Exception as exc:
        _state.init_error = str(exc)
        # Contexte minimal sans engine
        if _state.registry is None:
            _state.registry = make_default_registry()
        _state.ctx = CommandContext(
            engine=None,
            config=_state.config,
            event_bus=_state.event_bus,
            registry=_state.registry,
        )

    # --- Metriques (Phase 5(C)) — ring buffer in-memory ---
    _state.metrics_collector = MetricsCollector()

    # --- Sécurité API (Phase 4(B)) — initialisation non bloquante ---
    # Séparée du bloc principal : une erreur ici ne doit pas empêcher
    # l'API de démarrer (mode dégradé sans auth si erreur critique).
    try:
        if _state.config is not None:
            secrets_dir = _state.config.get_path("secrets")
            _state.key_manager = ApiKeyManager(secrets_dir)
            _state.key_manager.load_or_generate()
            rate_limit = int(_state.config.get("api.rate_limit_per_min", 60))
            _state.rate_limiter = RateLimiter(max_per_min=rate_limit)
            _state.session_manager = SessionManager()
            # Phase 6(D) — UserStore SQLite
            data_root = _state.config.get_path("data_root")
            _state.user_store = UserStore(data_root)
    except Exception as sec_exc:
        # Non bloquant : l'API démarre sans auth plutôt que de crash
        _state.init_error = (
            (_state.init_error or "") + f" | Security init error: {sec_exc}"
        )


# ---------------------------------------------------------------------------
# Lifespan FastAPI
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """
    Cycle de vie de l'application FastAPI.

    Startup  : initialise EVA dans un thread worker (code synchrone)
    Shutdown : arrêt propre du moteur
    """
    await asyncio.to_thread(_init_eva)
    yield
    if _state.engine and _state.engine.is_running:
        try:
            _state.engine.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Application FastAPI
# ---------------------------------------------------------------------------


app = FastAPI(
    title="EVA API",
    description=(
        "## EVA — Assistant IA Personnel\n\n"
        "API REST locale pour converser avec EVA via Ollama.\n\n"
        "---\n\n"
        "### Authentification\n\n"
        "Trois méthodes acceptées (par ordre de priorité) :\n\n"
        "```\n"
        "Authorization: Bearer <key>   # header standard (curl, SDK)\n"
        "X-EVA-Key: <key>              # header alternatif\n"
        "?api_key=<key>                # query param (EventSource navigateur)\n"
        "```\n\n"
        "Récupérer la clé :\n\n"
        "```bash\n"
        "eva --print-api-key           # affiche (ou génère) la clé\n"
        "# La clé est aussi affichée au démarrage : eva --api\n"
        "```\n\n"
        "---\n\n"
        "### Rate Limiting\n\n"
        "60 requêtes/minute par IP par défaut.\n"
        "Configurable via `api.rate_limit_per_min` dans `config.yaml`.\n"
        "Réponse : HTTP **429** + header `Retry-After: 60`.\n\n"
        "---\n\n"
        "### Endpoints\n\n"
        "| Endpoint | Auth | Rate limit | Description |\n"
        "|---|---|---|---|\n"
        "| `GET /health` | Non | Non | Healthcheck public |\n"
        "| `GET /status` | Oui | Non | État du moteur |\n"
        "| `POST /chat` | Oui | Oui | Réponse synchrone |\n"
        "| `GET /chat/stream` | Oui | Oui | Streaming SSE token par token |\n\n"
        "> **Note :** API conçue pour usage local uniquement (`127.0.0.1`).\n"
        "> Exposition réseau prévue en Phase 5 après validation du modèle auth."
    ),
    version=__version__,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "System",
            "description": "Healthcheck et statut du moteur EVA.",
        },
        {
            "name": "Auth",
            "description": (
                "Authentification par session cookie (Phase 6(A)).\n\n"
                "- `POST /auth/login` : valide la cle API, cree une session HttpOnly\n"
                "- `POST /auth/logout` : revoque la session"
            ),
        },
        {
            "name": "Chat",
            "description": (
                "Conversation avec EVA.\n\n"
                "- `POST /chat` : réponse synchrone complète (JSON)\n"
                "- `GET /chat/stream` : réponse en streaming SSE (token par token)"
            ),
        },
    ],
)


# ---------------------------------------------------------------------------
# Middleware HSTS (Phase 6(B)) — actif uniquement en mode TLS
# ---------------------------------------------------------------------------


@app.middleware("http")
async def hsts_middleware(request: Request, call_next):
    """
    Ajoute le header HSTS si l'API tourne en mode TLS.

    Strict-Transport-Security force le navigateur a utiliser HTTPS
    pour toutes les requetes suivantes pendant 1 an.
    N'est actif que si _state.tls == True (eva --api --tls).
    """
    response = await call_next(request)
    if _state.tls:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# ---------------------------------------------------------------------------
# Dépendances FastAPI — Auth + Rate Limiting (Phase 4(B))
# ---------------------------------------------------------------------------


async def require_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_eva_key: Optional[str] = Header(None, alias="X-EVA-Key"),
) -> None:
    """
    Dependance FastAPI : verifie l'authentification.

    Ordre de priorite :
        1. Cookie de session `eva_session` (web UI — Phase 6(A))
        2. Authorization: Bearer <key>  (header standard)
        3. X-EVA-Key: <key>             (header alternatif)

    Raises:
        HTTPException 503 : si key_manager non initialise
        HTTPException 401 : si aucune auth valide
    """
    if _state.key_manager is None:
        # Securite non initialisee (erreur startup) — service indisponible
        raise HTTPException(
            status_code=503,
            detail="Securite non initialisee. Relancez l'API.",
        )

    # 1. Cookie de session HttpOnly (web UI — Phase 6(A))
    session_id = request.cookies.get("eva_session", "")
    if session_id and _state.session_manager and _state.session_manager.verify(session_id):
        return

    # 2. Bearer / X-EVA-Key (backward compat clients API)
    api_key: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]
    elif x_eva_key:
        api_key = x_eva_key

    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Cle API requise. Header : Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Comparaison constant-time (pas de timing attack)
    if not _state.key_manager.verify(api_key):
        raise HTTPException(
            status_code=401,
            detail="Cle API invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def check_rate_limit(request: Request) -> None:
    """
    Dépendance FastAPI : vérifie le rate limit par IP.

    Rate limit configuré via api.rate_limit_per_min dans config.yaml.
    Si rate_limiter non initialisé : pas de limite (mode dégradé).

    Raises:
        HTTPException 429 : si IP dépasse la limite
    """
    if _state.rate_limiter is None:
        return  # Pas de rate limiter = pas de limite (mode dégradé)

    # Extraire l'IP cliente (TestClient → "testclient")
    client_ip = request.client.host if request.client else "unknown"

    if not _state.rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de requêtes. Limite : 60 req/min.",
            headers={"Retry-After": "60"},
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Healthcheck public",
    responses={
        200: {
            "description": "API opérationnelle (public — aucune auth requise).",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "version": "0.3.0"},
                }
            },
        }
    },
)
async def health() -> HealthResponse:
    """
    Healthcheck de l'API EVA.

    **Public** — Toujours 200 OK si l'API tourne (même en mode dégradé).
    Aucune authentification requise.

    Utile pour sonder la disponibilité de l'API sans clé.
    """
    return HealthResponse(status="ok", version=__version__)


@app.get(
    "/status",
    response_model=StatusResponse,
    tags=["System"],
    summary="État du moteur EVA",
    dependencies=[Depends(require_api_key)],
    responses={
        200: {
            "description": (
                "Toujours 200 — même si le moteur n'est pas démarré.\n\n"
                "`engine` : `\"RUNNING\"` | `\"STOPPED\"` | `\"UNAVAILABLE\"`"
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "running": {
                            "summary": "Moteur démarré",
                            "value": {
                                "engine": "RUNNING",
                                "provider": "ollama",
                                "components": {
                                    "memory": True,
                                    "prompt": True,
                                    "llm": True,
                                    "conversation": True,
                                },
                            },
                        },
                        "unavailable": {
                            "summary": "Moteur non disponible",
                            "value": {
                                "engine": "UNAVAILABLE",
                                "provider": None,
                                "components": {},
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Clé API manquante ou invalide.",
            "content": {
                "application/json": {
                    "example": {"detail": "Clé API requise. Header : Authorization: Bearer <key>"}
                }
            },
        },
    },
)
async def status() -> StatusResponse:
    """
    Retourne l'état du moteur EVA.

    **Auth requise** — Toujours HTTP 200 (même si moteur non démarré).
    `engine` vaut `"RUNNING"`, `"STOPPED"` ou `"UNAVAILABLE"`.

    Pratique pour vérifier qu'Ollama est bien connecté avant d'envoyer des messages.
    """
    if _state.engine is None:
        return StatusResponse(
            engine="UNAVAILABLE",
            provider=None,
            components={},
        )

    engine_status = _state.engine.status()
    is_running = engine_status.get("running", False)

    return StatusResponse(
        engine="RUNNING" if is_running else "STOPPED",
        provider="ollama",
        components=engine_status.get("components", {}),
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Envoyer un message à EVA (réponse synchrone)",
    dependencies=[Depends(require_api_key), Depends(check_rate_limit)],
    responses={
        200: {
            "description": "Réponse complète d'EVA (JSON).",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Bonjour ! Je suis EVA, votre assistant IA. Comment puis-je vous aider ?",
                        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                        "metadata": {"provider": "ollama", "latency_ms": 1240},
                    }
                }
            },
        },
        401: {
            "description": "Clé API manquante ou invalide.",
            "content": {
                "application/json": {
                    "example": {"detail": "Clé API requise. Header : Authorization: Bearer <key>"}
                }
            },
        },
        422: {
            "description": "Corps de requête invalide (message vide ou manquant).",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "message"],
                                "msg": "Le message ne peut pas être vide.",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
        429: {
            "description": "Trop de requêtes — limite 60 req/min dépassée.",
            "content": {
                "application/json": {
                    "example": {"detail": "Trop de requêtes. Limite : 60 req/min."}
                }
            },
        },
        500: {
            "description": "Erreur interne du moteur EVA.",
            "content": {
                "application/json": {
                    "example": {"detail": "Erreur lors du traitement."}
                }
            },
        },
        503: {
            "description": "Moteur EVA non démarré.",
            "content": {
                "application/json": {
                    "example": {"detail": "Moteur EVA non démarré. Utilisez /start ou relancez l'API."}
                }
            },
        },
    },
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Envoie un message à EVA et retourne la réponse structurée en JSON.

    **Auth requise + Rate limited** — 60 req/min par IP (configurable via `config.yaml`).
    L'appel LLM est non-bloquant (`asyncio.to_thread`).

    Si `conversation_id` est fourni, EVA poursuit la conversation existante.
    Sinon, un UUID est généré automatiquement.

    Préférez `GET /chat/stream` pour une UX avec affichage progressif des tokens.
    """
    if _state.engine is None or not _state.engine.is_running:
        raise HTTPException(
            status_code=503,
            detail="Moteur EVA non démarré. Utilisez /start ou relancez l'API.",
        )

    # Générer un conversation_id si non fourni par le client
    conv_id = request.conversation_id or str(uuid.uuid4())

    t0 = time.monotonic()
    try:
        response_text = await asyncio.to_thread(
            _state.engine.process, request.message
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        if _state.metrics_collector:
            _state.metrics_collector.record_chat(latency_ms, ok=True)

        return ChatResponse(
            response=response_text,
            conversation_id=conv_id,
            metadata=ChatMetadata(provider="ollama", latency_ms=latency_ms),
        )
    except Exception:
        if _state.metrics_collector:
            _state.metrics_collector.record_chat(
                int((time.monotonic() - t0) * 1000), ok=False
            )
        # F-04 audit sécurité R-043 : pas de detail=str(exc) — évite le leak
        # d'informations internes (chemin fichier, nom modèle, message réseau)
        # dans la réponse HTTP. L'exception est journalisée en interne.
        raise HTTPException(
            status_code=500,
            detail="Erreur lors du traitement.",
        )


@app.get(
    "/chat/stream",
    tags=["Chat"],
    summary="Streaming SSE (token par token)",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "Stream SSE text/event-stream.\n\n"
                "Événements émis :\n"
                "- `event: meta` — `{conversation_id, provider}`\n"
                "- `event: token` — `{text}` (répété N fois)\n"
                "- `event: done` — `{latency_ms, ok: true}`\n"
                "- `event: error` — `{message}` (fin de stream)"
            ),
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "example": (
                        "event: meta\ndata: {\"conversation_id\": \"uuid\", \"provider\": \"ollama\"}\n\n"
                        "event: token\ndata: {\"text\": \"Bonjour\"}\n\n"
                        "event: done\ndata: {\"latency_ms\": 420, \"ok\": true}\n\n"
                    ),
                }
            },
        },
        401: {"description": "Clé API manquante ou invalide."},
        429: {"description": "Trop de requêtes — limite 60 req/min dépassée."},
        503: {"description": "Moteur EVA non démarré ou sécurité non initialisée."},
    },
)
async def chat_stream(
    request: Request,
    message: str = Query(..., min_length=1, max_length=2000,
                         description="Message envoyé à EVA."),
    conversation_id: Optional[str] = Query(None,
                                           description="ID conversation (optionnel)."),
    api_key: Optional[str] = Query(None,
                                   description="Clé API EVA (pour EventSource navigateur)."),
    authorization: Optional[str] = Header(None),
    x_eva_key: Optional[str] = Header(None, alias="X-EVA-Key"),
) -> StreamingResponse:
    """
    GET /chat/stream — Streaming SSE token par token.

    **Auth requise + Rate limited.**

    Accepte la clé via (par ordre de priorité) :

    - Header `Authorization: Bearer <key>`  (usage programmatique / curl)
    - Header `X-EVA-Key: <key>`             (fallback header)
    - Query param `?api_key=<key>`          (EventSource navigateur — headers non supportés)

    **Protocole SSE :**

    ```
    event: meta   → {"conversation_id": "...", "provider": "ollama"}
    event: token  → {"text": "chunk"}       (N fois)
    event: done   → {"latency_ms": N, "ok": true}
    event: error  → {"message": "..."}      (fin de stream)
    ```

    Streaming natif OllamaProvider (Phase 5A) — tokens Ollama NDJSON en temps reel.
    """
    # --- Auth inline (supporte cookie session + query param pour EventSource) ---
    if _state.key_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Securite non initialisee. Relancez l'API.",
        )
    authed = False
    # 1. Cookie de session (EventSource navigateur envoie les cookies auto)
    session_id = request.cookies.get("eva_session", "")
    if session_id and _state.session_manager and _state.session_manager.verify(session_id):
        authed = True
    # 2. Bearer / X-EVA-Key / ?api_key= (backward compat API clients)
    if not authed:
        provided: Optional[str] = None
        if authorization and authorization.startswith("Bearer "):
            provided = authorization[7:]
        elif x_eva_key:
            provided = x_eva_key
        elif api_key:
            provided = api_key
        if provided is not None and _state.key_manager.verify(provided):
            authed = True
    if not authed:
        raise HTTPException(
            status_code=401,
            detail="Cle API requise ou invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Rate limit ---
    if _state.rate_limiter is not None:
        client_ip = request.client.host if request.client else "unknown"
        if not _state.rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Trop de requêtes. Limite : 60 req/min.",
                headers={"Retry-After": "60"},
            )

    # --- Engine check ---
    if _state.engine is None or not _state.engine.is_running:
        raise HTTPException(
            status_code=503,
            detail="Moteur EVA non démarré. Utilisez /start ou relancez l'API.",
        )

    async def _event_generator() -> AsyncGenerator[str, None]:
        """
        Generateur SSE — streaming natif OllamaProvider (Phase 5A).

        Bridge sync generator (process_stream) -> async SSE via asyncio.Queue.
        Protocole : event:meta -> event:token* -> event:done | event:error
        """
        conv_id = conversation_id or str(uuid.uuid4())
        t0 = time.monotonic()

        yield (
            f"event: meta\n"
            f"data: {json.dumps({'conversation_id': conv_id, 'provider': 'ollama'})}\n\n"
        )

        queue: asyncio.Queue = asyncio.Queue()
        error_list: list = []
        loop = asyncio.get_event_loop()

        def _run_stream() -> None:
            try:
                for token in _state.engine.process_stream(message):  # type: ignore[union-attr]
                    if token:
                        loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as exc:
                # F-05 securite : ne pas exposer str(exc) dans la reponse
                error_list.append(exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel fin

        stream_task = asyncio.create_task(asyncio.to_thread(_run_stream))

        # Phase 5(C) — TTFT tracking
        first_token_time: Optional[float] = None
        token_count: int = 0

        try:
            while True:
                token = await queue.get()
                if token is None:
                    break
                if first_token_time is None:
                    first_token_time = time.monotonic()
                token_count += 1
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except Exception:
            if _state.metrics_collector:
                _state.metrics_collector.record_stream(
                    int((time.monotonic() - t0) * 1000), None, token_count, ok=False
                )
            yield f"event: error\ndata: {json.dumps({'message': 'Erreur lors du traitement.'})}\n\n"
            return
        finally:
            await stream_task

        if error_list:
            if _state.metrics_collector:
                _state.metrics_collector.record_stream(
                    int((time.monotonic() - t0) * 1000), None, token_count, ok=False
                )
            yield f"event: error\ndata: {json.dumps({'message': 'Erreur lors du traitement.'})}\n\n"
            return

        # Calculs finaux — Phase 5(C)
        latency_ms = int((time.monotonic() - t0) * 1000)
        ttft_ms = int((first_token_time - t0) * 1000) if first_token_time else None
        stream_s = (latency_ms - ttft_ms) / 1000 if ttft_ms else 0
        tps = round(token_count / stream_s, 1) if stream_s > 0 else None

        if _state.metrics_collector:
            _state.metrics_collector.record_stream(latency_ms, ttft_ms, token_count, ok=True)

        # event:done enrichi (additif — non breaking)
        done_data: dict = {"latency_ms": latency_ms, "ok": True}
        if ttft_ms is not None:
            done_data["ttft_ms"] = ttft_ms
        if token_count > 0:
            done_data["tokens"] = token_count
        if tps is not None:
            done_data["tokens_per_sec"] = tps
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /metrics — Phase 5(C)
# ---------------------------------------------------------------------------


@app.get(
    "/metrics",
    tags=["System"],
    summary="Metriques de performance API (p50/p95, TTFT SSE)",
    dependencies=[Depends(require_api_key)],
    responses={
        200: {
            "description": "Metriques p50/p95 par endpoint (ring buffer 100 dernieres requetes).",
            "content": {
                "application/json": {
                    "example": {
                        "uptime_s": 42,
                        "endpoints": {
                            "chat": {
                                "requests": 10, "errors": 0,
                                "p50_ms": 215, "p95_ms": 890,
                                "last_latency_ms": 201
                            },
                            "chat_stream": {
                                "requests": 4, "errors": 0,
                                "p50_ms": 1240, "p95_ms": 3200,
                                "p50_ttft_ms": 180, "p95_ttft_ms": 420,
                                "last_latency_ms": 1100,
                                "last_ttft_ms": 175,
                                "last_token_count": 47,
                                "last_tokens_per_sec": 12.3
                            }
                        }
                    }
                }
            }
        },
        401: {"description": "Cle API manquante ou invalide."},
        503: {"description": "Metriques non disponibles."},
    },
)
async def get_metrics():
    """
    Expose les metriques de performance API (ring buffer, 100 dernieres requetes).

    - `p50_ms` / `p95_ms` : latence totale par endpoint
    - `p50_ttft_ms` / `p95_ttft_ms` : time-to-first-token SSE
    - `last_*` : chiffres de la derniere requete

    **Auth requise** (meme cle que /status et /chat).
    """
    if _state.metrics_collector is None:
        raise HTTPException(
            status_code=503,
            detail="Metrics collector not initialized.",
        )
    from fastapi.responses import JSONResponse as _JSONResponse
    return _JSONResponse(_state.metrics_collector.get_summary())


# ---------------------------------------------------------------------------
# Auth — Session cookie (Phase 6(A))
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """
    Corps de la requete POST /auth/login.

    Deux modes (mutuellement exclusifs) :
        1. api_key seul  — backward compat (scripts, clients existants)
        2. username + password — Phase 6(D) multi-utilisateurs
    """

    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class RegisterRequest(BaseModel):
    """Corps de la requete POST /auth/register."""

    username: str
    password: str
    role: str = "user"  # "admin" | "user"


class MeResponse(BaseModel):
    """Reponse de GET /me."""

    username: Optional[str]
    role: Optional[str]
    authenticated: bool


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Helper : pose le cookie eva_session avec les bons flags."""
    response.set_cookie(
        key="eva_session",
        value=session_id,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=SessionManager.TTL,
        secure=_state.tls,
    )


@app.post(
    "/auth/login",
    tags=["Auth"],
    summary="Demarrer une session (cookie HttpOnly)",
    responses={
        200: {"description": "Session creee. Cookie eva_session set."},
        400: {"description": "Corps de requete invalide."},
        401: {"description": "Credentials invalides."},
        503: {"description": "Service non initialise."},
    },
)
async def auth_login(body: LoginRequest, response: Response) -> dict:
    """
    Cree une session via cookie HttpOnly/SameSite=Strict.

    Deux modes :
    - **api_key** : valide la cle API globale (backward compat)
    - **username + password** : valide contre la base utilisateurs (Phase 6(D))

    Si des utilisateurs existent et que username+password est fourni,
    la session est associee au user_id.
    """
    if _state.session_manager is None:
        raise HTTPException(status_code=503, detail="Service non initialise.")

    user_id: Optional[int] = None

    # --- Mode username+password (Phase 6(D)) ---
    if body.username is not None or body.password is not None:
        if not body.username or not body.password:
            raise HTTPException(
                status_code=400,
                detail="username et password requis ensemble.",
            )
        if _state.user_store is None:
            raise HTTPException(status_code=503, detail="Service non initialise.")
        user = _state.user_store.authenticate(body.username, body.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Identifiants invalides.")
        user_id = user.id

    # --- Mode api_key (backward compat) ---
    elif body.api_key is not None:
        if _state.key_manager is None:
            raise HTTPException(status_code=503, detail="Service non initialise.")
        if not _state.key_manager.verify(body.api_key):
            raise HTTPException(status_code=401, detail="Cle API invalide.")

    else:
        raise HTTPException(
            status_code=400,
            detail="Fournir api_key OU username+password.",
        )

    session_id = _state.session_manager.create(user_id=user_id)
    _set_session_cookie(response, session_id)
    return {"status": "ok"}


@app.post(
    "/auth/register",
    tags=["Auth"],
    summary="Creer un utilisateur (admin uniquement)",
    responses={
        200: {"description": "Utilisateur cree."},
        400: {"description": "Donnees invalides ou username deja existant."},
        401: {"description": "Non authentifie ou role insuffisant."},
        503: {"description": "Service non initialise."},
    },
    dependencies=[Depends(require_api_key)],
)
async def auth_register(body: RegisterRequest, request: Request) -> dict:
    """
    Cree un nouvel utilisateur local.

    Accessible uniquement aux admins (ou via api-key globale pour le
    premier admin — bootstrap).
    """
    if _state.user_store is None or _state.session_manager is None:
        raise HTTPException(status_code=503, detail="Service non initialise.")

    # Verifier que le demandeur est admin (si des utilisateurs existent)
    if _state.user_store.has_admin():
        session_id = request.cookies.get("eva_session", "")
        caller_user_id = _state.session_manager.get_user_id(session_id)
        if caller_user_id is not None:
            caller = _state.user_store.get_by_id(caller_user_id)
            if caller is None or caller.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=401,
                    detail="Role admin requis pour creer un utilisateur.",
                )
        # Si caller_user_id est None : connexion api-key => admin implicite OK

    # Valider le role
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Role invalide '{body.role}'. Valeurs acceptees : admin, user.",
        )

    try:
        user = _state.user_store.create_user(body.username, body.password, role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "ok", "username": user.username, "role": user.role.value}


@app.get(
    "/me",
    tags=["Auth"],
    summary="Profil de l'utilisateur courant",
    responses={
        200: {"description": "Informations utilisateur courant."},
    },
    dependencies=[Depends(require_api_key)],
)
async def me(request: Request) -> MeResponse:
    """
    Retourne le profil de l'utilisateur authentifie.

    Si la session est anonyme (login par api-key), retourne authenticated=True
    sans username ni role.
    """
    session_id = request.cookies.get("eva_session", "")
    if session_id and _state.session_manager:
        user_id = _state.session_manager.get_user_id(session_id)
        if user_id is not None and _state.user_store:
            user = _state.user_store.get_by_id(user_id)
            if user:
                return MeResponse(
                    username=user.username,
                    role=user.role.value,
                    authenticated=True,
                )
    return MeResponse(username=None, role=None, authenticated=True)


@app.post(
    "/auth/logout",
    tags=["Auth"],
    summary="Terminer la session (supprime le cookie)",
    responses={200: {"description": "Session revoquee."}},
)
async def auth_logout(request: Request, response: Response) -> dict:
    """
    Revoque la session courante et supprime le cookie eva_session.

    Idempotent : sans effet si aucune session active.
    """
    session_id = request.cookies.get("eva_session", "")
    if session_id and _state.session_manager:
        _state.session_manager.revoke(session_id)
    response.delete_cookie(key="eva_session", path="/")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main(host: str = "127.0.0.1", port: int = 8000, tls: bool = False) -> int:
    """
    Lance le serveur API EVA.

    Affiche la clé API AVANT le démarrage uvicorn (lisible dans le terminal).

    Args:
        host: Adresse d'écoute.
              Phase 4 security rule: API bound to 127.0.0.1 (auth ajoutée).
        port: Port d'écoute (défaut : 8000)
        tls:  Active HTTPS avec certificat auto-signé (Phase 6(B)).
              Génère eva/data/certs/server.crt + server.key au 1er lancement.

    Returns:
        Code de sortie (0 = normal, 1 = erreur)
    """
    # Pré-charger la clé pour l'afficher AVANT le démarrage du serveur
    # (le lifespan la rechargera depuis le même fichier)
    _api_key: Optional[str] = None
    try:
        _cfg = ConfigManager()
        _km = ApiKeyManager(_cfg.get_path("secrets"))
        _api_key = _km.load_or_generate()
    except Exception:
        pass

    # Mode TLS : générer / vérifier le certificat
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    if tls:
        try:
            from eva.api.tls import CertManager
            _cfg2 = ConfigManager()
            cert_mgr = CertManager(_cfg2.get_path("data_root"))
            cert_path, key_path = cert_mgr.ensure()
            ssl_certfile = str(cert_path)
            ssl_keyfile = str(key_path)
            # Activer le flag TLS dans l'état partagé (cookie Secure + HSTS)
            _state.tls = True
        except Exception as exc:
            print(f"Erreur TLS : {exc}")
            return 1

    scheme = "https" if tls else "http"
    try:
        import uvicorn

        print(f"EVA API v{__version__} — {scheme}://{host}:{port}")
        if tls:
            print("  TLS   : certificat auto-signé (eva/data/certs/)")
            print("  Note  : acceptez l'avertissement navigateur (cert non-CA)")
        if _api_key:
            print(f"  API Key : {_api_key}")
        print(f"  Docs  : {scheme}://{host}:{port}/docs")
        print(f"  Redoc : {scheme}://{host}:{port}/redoc")

        uvicorn_kwargs: dict = {"host": host, "port": port}
        if ssl_certfile and ssl_keyfile:
            uvicorn_kwargs["ssl_certfile"] = ssl_certfile
            uvicorn_kwargs["ssl_keyfile"] = ssl_keyfile

        uvicorn.run(app, **uvicorn_kwargs)
        return 0
    except ImportError:
        print(
            "uvicorn non installé. "
            "Installez-le : pip install 'fastapi[standard]'"
        )
        return 1
    except Exception as exc:
        print(f"Erreur API : {exc}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
