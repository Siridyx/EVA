"""
Tests de l'API REST FastAPI (R-031).

Stratégie :
- TestClient de Starlette (synchrone, sans lifespan — pas d'init EVA réelle)
- Modifier eva.api.app._state directement pour mocker le moteur
- Tests des 3 endpoints : /health, /status, /chat
- Tests des schémas Pydantic et de la configuration CLI

Standards :
- Python 3.9 strict
- Isolation : reset _state après chaque test (fixture autouse)
- Pas d'accès réseau
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import conditionnel : fastapi requis
# ---------------------------------------------------------------------------

try:
    import sys
    from fastapi.testclient import TestClient

    # Importer depuis le module pour le charger dans sys.modules
    from eva.api.app import (
        ChatRequest,
        ChatResponse,
        EvaState,
        HealthResponse,
        StatusResponse,
        app,
        main,
    )

    # Accéder au vrai module Python via sys.modules
    # (évite le conflit avec l'attribut 'app' du package eva.api)
    api_module = sys.modules["eva.api.app"]

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

requires_fastapi = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="fastapi non installé — pip install 'fastapi[standard]'",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """
    TestClient FastAPI SANS lifespan.

    Sans context manager = lifespan non exécuté = pas d'init EVA réelle.
    _state.engine reste None sauf si le test le définit.
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Réinitialise _state du module API après chaque test."""
    yield
    if FASTAPI_AVAILABLE:
        api_module._state.engine = None
        api_module._state.config = None
        api_module._state.event_bus = None
        api_module._state.registry = None
        api_module._state.ctx = None
        api_module._state.init_error = None


@pytest.fixture
def mock_engine_running():
    """EVAEngine mocké en état RUNNING."""
    engine = MagicMock()
    engine.is_running = True
    engine.status.return_value = {
        "name": "EVAEngine",
        "running": True,
        "started": True,
        "pipeline_mode": "sequential",
        "pipeline_initialized": True,
        "components": {
            "llm": True,
            "memory": True,
            "conversation": True,
        },
    }
    engine.process.return_value = "Réponse de test EVA."
    return engine


@pytest.fixture
def mock_engine_stopped():
    """EVAEngine mocké en état STOPPED."""
    engine = MagicMock()
    engine.is_running = False
    engine.status.return_value = {
        "name": "EVAEngine",
        "running": False,
        "started": False,
        "pipeline_mode": "sequential",
        "pipeline_initialized": False,
        "components": {
            "llm": False,
            "memory": False,
            "conversation": False,
        },
    }
    return engine


# ---------------------------------------------------------------------------
# 1. Tests GET /health
# ---------------------------------------------------------------------------


@requires_fastapi
class TestHealthEndpoint:
    """Tests de l'endpoint GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_ok(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_has_version(self, client):
        from eva import __version__
        response = client.get("/health")
        data = response.json()
        assert data["version"] == __version__

    def test_health_always_200_even_no_engine(self, client):
        """Health retourne toujours 200, même si moteur non initialisé."""
        api_module._state.engine = None
        response = client.get("/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. Tests GET /status
# ---------------------------------------------------------------------------


@requires_fastapi
class TestStatusEndpoint:
    """Tests de l'endpoint GET /status."""

    def test_status_returns_200_with_engine(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_running_true(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.get("/status")
        assert response.json()["running"] is True

    def test_status_running_false(self, client, mock_engine_stopped):
        api_module._state.engine = mock_engine_stopped
        response = client.get("/status")
        assert response.json()["running"] is False

    def test_status_has_components(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.get("/status")
        assert "components" in response.json()

    def test_status_503_when_engine_none(self, client):
        api_module._state.engine = None
        response = client.get("/status")
        assert response.status_code == 503

    def test_status_503_detail_message(self, client):
        api_module._state.engine = None
        response = client.get("/status")
        assert "non initialisé" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Tests POST /chat
# ---------------------------------------------------------------------------


@requires_fastapi
class TestChatEndpoint:
    """Tests de l'endpoint POST /chat."""

    def test_chat_returns_200(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": "Bonjour EVA"})
        assert response.status_code == 200

    def test_chat_response_ok_true(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": "Test"})
        assert response.json()["ok"] is True

    def test_chat_response_has_text(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": "Bonjour"})
        assert "response" in response.json()
        assert len(response.json()["response"]) > 0

    def test_chat_calls_engine_process(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        client.post("/chat", json={"message": "Appel test"})
        mock_engine_running.process.assert_called_once_with("Appel test")

    def test_chat_empty_message_422(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 422

    def test_chat_whitespace_message_422(self, client, mock_engine_running):
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": "   "})
        assert response.status_code == 422

    def test_chat_engine_none_503(self, client):
        api_module._state.engine = None
        response = client.post("/chat", json={"message": "Test"})
        assert response.status_code == 503

    def test_chat_engine_stopped_503(self, client, mock_engine_stopped):
        api_module._state.engine = mock_engine_stopped
        response = client.post("/chat", json={"message": "Test"})
        assert response.status_code == 503

    def test_chat_engine_process_error_500(self, client, mock_engine_running):
        mock_engine_running.process.side_effect = RuntimeError("Erreur LLM")
        api_module._state.engine = mock_engine_running
        response = client.post("/chat", json={"message": "Test"})
        assert response.status_code == 500

    def test_chat_missing_message_field_422(self, client):
        """Corps sans champ 'message' → validation Pydantic 422."""
        response = client.post("/chat", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 4. Tests des schémas Pydantic
# ---------------------------------------------------------------------------


@requires_fastapi
class TestAPISchema:
    """Tests de validation des schémas Pydantic."""

    def test_chat_request_valid(self):
        req = ChatRequest(message="Bonjour")
        assert req.message == "Bonjour"

    def test_chat_response_valid(self):
        resp = ChatResponse(response="Réponse", ok=True)
        assert resp.response == "Réponse"
        assert resp.ok is True

    def test_status_response_valid(self):
        s = StatusResponse(
            running=True,
            started=True,
            pipeline_mode="sequential",
            pipeline_initialized=True,
            components={"llm": True, "memory": True, "conversation": True},
        )
        assert s.running is True
        assert "llm" in s.components

    def test_health_response_valid(self):
        h = HealthResponse(status="ok", version="0.2.0-p2")
        assert h.status == "ok"
        assert h.version == "0.2.0-p2"

    def test_eva_state_defaults(self):
        state = EvaState()
        assert state.engine is None
        assert state.config is None
        assert state.init_error is None


# ---------------------------------------------------------------------------
# 5. Tests de la configuration de l'app
# ---------------------------------------------------------------------------


@requires_fastapi
class TestAPIInit:
    """Tests de la configuration FastAPI."""

    def test_app_title(self):
        assert app.title == "EVA API"

    def test_app_version_matches_eva(self):
        from eva import __version__
        assert app.version == __version__

    def test_app_has_health_route(self):
        routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
        assert "/health" in routes

    def test_app_has_status_route(self):
        routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
        assert "/status" in routes

    def test_app_has_chat_route(self):
        routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
        assert "/chat" in routes


# ---------------------------------------------------------------------------
# 6. Tests du flag --api dans CLI
# ---------------------------------------------------------------------------


class TestCLIApiFlag:
    """Tests du flag --api dans eva/cli.py."""

    def test_cli_has_api_flag(self):
        import eva.cli
        source = Path(eva.cli.__file__).read_text(encoding="utf-8")
        assert "--api" in source

    def test_cli_imports_api_conditionally(self):
        import eva.cli
        source = Path(eva.cli.__file__).read_text(encoding="utf-8")
        assert "api_main" in source

    def test_cli_docstring_has_api(self):
        import eva.cli
        assert eva.cli.__doc__ is not None
        assert "--api" in eva.cli.__doc__

    def test_cli_api_before_tui_in_dispatch(self):
        """--api doit être prioritaire sur --tui dans le dispatch."""
        import eva.cli
        source = Path(eva.cli.__file__).read_text(encoding="utf-8")
        api_pos = source.index("api_main")
        tui_pos = source.index("tui_main")
        assert api_pos < tui_pos


# ---------------------------------------------------------------------------
# 7. Tests du module __init__.py API
# ---------------------------------------------------------------------------


class TestApiInit:
    """Tests du module eva.api."""

    def test_api_module_importable(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("fastapi non installé")
        import eva.api
        assert eva.api is not None

    def test_api_exports_app(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("fastapi non installé")
        from eva.api import app, main
        assert app is not None
        assert main is not None

    def test_main_function_importable(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("fastapi non installé")
        from eva.api.app import main as api_main
        assert callable(api_main)
