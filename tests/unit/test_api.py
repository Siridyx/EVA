"""
Tests de l'API REST FastAPI (R-031) — 4 tests essentiels.

Stratégie :
- TestClient Starlette (synchrone, sans lifespan — pas d'init EVA réelle)
- Modifier eva.api.app._state directement pour mocker le moteur
- 4 tests couvrant les 3 endpoints et la validation

Standards :
- Python 3.9 strict
- Isolation : reset _state après chaque test (fixture autouse)
- Pas d'accès réseau
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import conditionnel : fastapi requis
# ---------------------------------------------------------------------------

try:
    import sys
    from fastapi.testclient import TestClient

    from eva.api.app import app

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
    return TestClient(app, raise_server_exceptions=False)


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
def mock_engine():
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


# ---------------------------------------------------------------------------
# 4 tests essentiels
# ---------------------------------------------------------------------------


@requires_fastapi
def test_health_ok(client):
    """GET /health → 200 avec status=ok et version."""
    from eva import __version__

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__


@requires_fastapi
def test_status_returns_200(client, mock_engine):
    """GET /status → toujours 200, même sans engine."""
    # Sans engine : UNAVAILABLE
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["engine"] == "UNAVAILABLE"

    # Avec engine RUNNING
    api_module._state.engine = mock_engine
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["engine"] == "RUNNING"


@requires_fastapi
def test_chat_returns_response(client, mock_engine):
    """POST /chat → 200 avec response, conversation_id, metadata."""
    api_module._state.engine = mock_engine
    response = client.post("/chat", json={"message": "Bonjour EVA"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "metadata" in data
    assert data["metadata"]["provider"] == "ollama"
    assert isinstance(data["metadata"]["latency_ms"], int)


@requires_fastapi
def test_chat_validation_error(client, mock_engine):
    """POST /chat message vide → 422 (validation Pydantic)."""
    api_module._state.engine = mock_engine
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422
