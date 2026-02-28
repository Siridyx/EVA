"""
Tests de l'API REST FastAPI (R-031 + Phase 4(B) auth) — 10 tests.

Stratégie :
- TestClient Starlette (synchrone, sans lifespan — pas d'init EVA réelle)
- Modifier eva.api.app._state directement pour mocker le moteur et le key_manager
- 10 tests couvrant les 3 endpoints, la validation et l'auth/rate-limit

Standards :
- Python 3.9 strict
- Isolation : reset _state après chaque test (fixture autouse)
- Pas d'accès réseau
"""

from __future__ import annotations

import secrets as _secrets_module
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
# Constantes auth (Phase 4(B))
# ---------------------------------------------------------------------------

TEST_API_KEY = "test_api_key_abcdef1234567890abcdef"
VALID_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}


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
        api_module._state.key_manager = None
        api_module._state.rate_limiter = None


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


@pytest.fixture
def mock_key_manager():
    """ApiKeyManager mocké — accepte uniquement TEST_API_KEY."""
    mgr = MagicMock()
    mgr.verify.side_effect = lambda k: _secrets_module.compare_digest(
        k, TEST_API_KEY
    )
    mgr.key = TEST_API_KEY
    return mgr


# ---------------------------------------------------------------------------
# Tests existants (mis à jour Phase 4(B))
# ---------------------------------------------------------------------------


@requires_fastapi
def test_health_ok(client):
    """GET /health → 200 avec status=ok et version (endpoint public, sans auth)."""
    from eva import __version__

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__


@requires_fastapi
def test_status_returns_200(client, mock_engine, mock_key_manager):
    """GET /status → toujours 200 avec clé valide, même sans engine."""
    api_module._state.key_manager = mock_key_manager

    # Sans engine : UNAVAILABLE
    response = client.get("/status", headers=VALID_HEADERS)
    assert response.status_code == 200
    assert response.json()["engine"] == "UNAVAILABLE"

    # Avec engine RUNNING
    api_module._state.engine = mock_engine
    response = client.get("/status", headers=VALID_HEADERS)
    assert response.status_code == 200
    assert response.json()["engine"] == "RUNNING"


@requires_fastapi
def test_chat_returns_response(client, mock_engine, mock_key_manager):
    """POST /chat → 200 avec response, conversation_id, metadata (clé valide)."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    response = client.post(
        "/chat", json={"message": "Bonjour EVA"}, headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "metadata" in data
    assert data["metadata"]["provider"] == "ollama"
    assert isinstance(data["metadata"]["latency_ms"], int)


@requires_fastapi
def test_chat_validation_error(client, mock_engine, mock_key_manager):
    """POST /chat message vide → 422 (validation Pydantic, après auth réussie)."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    response = client.post(
        "/chat", json={"message": ""}, headers=VALID_HEADERS
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Nouveaux tests Phase 4(B) — Auth + Rate Limiting
# ---------------------------------------------------------------------------


@requires_fastapi
def test_health_no_auth_ok(client):
    """/health sans clé → 200 (endpoint public)."""
    assert client.get("/health").status_code == 200


@requires_fastapi
def test_status_no_auth_401(client, mock_key_manager):
    """/status sans clé → 401."""
    api_module._state.key_manager = mock_key_manager
    assert client.get("/status").status_code == 401


@requires_fastapi
def test_chat_no_auth_401(client, mock_engine, mock_key_manager):
    """/chat sans clé → 401."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    assert client.post("/chat", json={"message": "test"}).status_code == 401


@requires_fastapi
def test_chat_invalid_auth_401(client, mock_engine, mock_key_manager):
    """/chat avec clé invalide → 401."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    response = client.post(
        "/chat",
        json={"message": "test"},
        headers={"Authorization": "Bearer mauvaise_cle"},
    )
    assert response.status_code == 401


@requires_fastapi
def test_chat_valid_auth_ok(client, mock_engine, mock_key_manager):
    """/chat avec clé valide → 200."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    response = client.post(
        "/chat", json={"message": "test"}, headers=VALID_HEADERS
    )
    assert response.status_code == 200


@requires_fastapi
def test_rate_limit_429(client, mock_engine, mock_key_manager):
    """4e requête avec limite=3 → 429."""
    from eva.api.security import RateLimiter

    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    api_module._state.rate_limiter = RateLimiter(max_per_min=3)

    for _ in range(3):
        assert (
            client.post(
                "/chat", json={"message": "test"}, headers=VALID_HEADERS
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/chat", json={"message": "test"}, headers=VALID_HEADERS
        ).status_code
        == 429
    )
