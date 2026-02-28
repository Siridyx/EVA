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

Future phases :
    - Streaming SSE (Phase 4(C))
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
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, field_validator

from eva import __version__
from eva.api.security import ApiKeyManager, RateLimiter
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
        "Assistant IA Personnel — API REST (R-031 + Phase 4(B) Auth)\n\n"
        "Authentification :\n"
        "- Header `Authorization: Bearer <key>` (principal)\n"
        "- Header `X-EVA-Key: <key>` (fallback)\n\n"
        "Endpoints :\n"
        "- `GET /health` : healthcheck **public** (toujours 200)\n"
        "- `GET /status` : état du moteur (auth requise)\n"
        "- `POST /chat` : envoyer un message (auth + rate limit)"
    ),
    version=__version__,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Dépendances FastAPI — Auth + Rate Limiting (Phase 4(B))
# ---------------------------------------------------------------------------


async def require_api_key(
    authorization: Optional[str] = Header(None),
    x_eva_key: Optional[str] = Header(None, alias="X-EVA-Key"),
) -> None:
    """
    Dépendance FastAPI : vérifie la clé API.

    Accepte :
        Authorization: Bearer <key>   (standard)
        X-EVA-Key: <key>              (fallback pratique)

    Raises:
        HTTPException 503 : si key_manager non initialisé
        HTTPException 401 : si clé absente ou invalide
    """
    if _state.key_manager is None:
        # Sécurité non initialisée (erreur startup) — service indisponible
        raise HTTPException(
            status_code=503,
            detail="Sécurité non initialisée. Relancez l'API.",
        )

    # Extraire la clé depuis le header prioritaire ou le fallback
    api_key: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]
    elif x_eva_key:
        api_key = x_eva_key

    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Clé API requise. Header : Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Comparaison constant-time (pas de timing attack)
    if not _state.key_manager.verify(api_key):
        raise HTTPException(
            status_code=401,
            detail="Clé API invalide.",
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


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    """
    Healthcheck de l'API EVA.

    **Public** — Toujours 200 OK si l'API tourne (même en mode dégradé).
    Aucune authentification requise.
    """
    return HealthResponse(status="ok", version=__version__)


@app.get(
    "/status",
    response_model=StatusResponse,
    tags=["System"],
    dependencies=[Depends(require_api_key)],
)
async def status() -> StatusResponse:
    """
    Retourne l'état du moteur EVA.

    **Auth requise** — Toujours HTTP 200 (même si moteur non démarré).
    `engine` vaut "RUNNING", "STOPPED" ou "UNAVAILABLE".
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
    dependencies=[Depends(require_api_key), Depends(check_rate_limit)],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Envoie un message à EVA et retourne la réponse structurée.

    **Auth requise + Rate limited** — 60 req/min par IP (configurable).
    L'appel LLM est non-bloquant (asyncio.to_thread).
    """
    if _state.engine is None or not _state.engine.is_running:
        raise HTTPException(
            status_code=503,
            detail="Moteur EVA non démarré. Utilisez /start ou relancez l'API.",
        )

    # Générer un conversation_id si non fourni par le client
    conv_id = request.conversation_id or str(uuid.uuid4())

    try:
        t0 = time.monotonic()
        response_text = await asyncio.to_thread(
            _state.engine.process, request.message
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        return ChatResponse(
            response=response_text,
            conversation_id=conv_id,
            metadata=ChatMetadata(provider="ollama", latency_ms=latency_ms),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement : {exc}",
        )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main(host: str = "127.0.0.1", port: int = 8000) -> int:
    """
    Lance le serveur API EVA.

    Affiche la clé API AVANT le démarrage uvicorn (lisible dans le terminal).

    Args:
        host: Adresse d'écoute.
              Phase 4 security rule: API bound to 127.0.0.1 (auth ajoutée).
              Phase 5 pourra ouvrir à 0.0.0.0 après validation du modèle auth.
        port: Port d'écoute (défaut : 8000)

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

    try:
        import uvicorn

        print(f"EVA API v{__version__} — http://{host}:{port}")
        if _api_key:
            print(f"  API Key : {_api_key}")
        print(f"  Docs  : http://{host}:{port}/docs")
        print(f"  Redoc : http://{host}:{port}/redoc")
        uvicorn.run(app, host=host, port=port)
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
