"""
Tests de l'API REST FastAPI (R-031 + Phase 4(B) auth + Phase 4(C) SSE) — 13 tests.

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
        api_module._state.metrics_collector = None


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
    engine.process.return_value = "Reponse de test EVA."
    engine.process_stream.return_value = ["Reponse", " de test EVA."]
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


# ---------------------------------------------------------------------------
# Tests Phase 4(C) — SSE streaming (/chat/stream)
# ---------------------------------------------------------------------------


@requires_fastapi
def test_stream_no_auth_401(client, mock_engine, mock_key_manager):
    """GET /chat/stream sans auth → 401 (auth vérifiée avant engine check)."""
    api_module._state.key_manager = mock_key_manager
    api_module._state.engine = mock_engine
    r = client.get("/chat/stream", params={"message": "test"})
    assert r.status_code == 401


@requires_fastapi
def test_stream_engine_not_started_503(client, mock_key_manager):
    """GET /chat/stream auth valide mais engine None → 503."""
    api_module._state.key_manager = mock_key_manager
    # engine reste None (reset_state)
    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": TEST_API_KEY},
    )
    assert r.status_code == 503


@requires_fastapi
def test_stream_valid_auth_200(client, mock_engine, mock_key_manager):
    """GET /chat/stream auth valide → 200, text/event-stream, meta + token + done."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": TEST_API_KEY},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    assert "event: meta" in r.text
    assert "event: token" in r.text
    assert "event: done" in r.text


# ---------------------------------------------------------------------------
# Tests Phase 4(E) — Audit sécurité R-043
# ---------------------------------------------------------------------------


@requires_fastapi
def test_chat_bearer_empty_key_401(client, mock_engine, mock_key_manager):
    """
    Authorization: Bearer <espace> → 401.

    F-01 : "Bearer " (espace après Bearer, pas de clé) → extrait "" →
    verify("") = False → 401. Pas de bypass.
    """
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    r = client.post(
        "/chat",
        json={"message": "test"},
        headers={"Authorization": "Bearer "},
    )
    assert r.status_code == 401


@requires_fastapi
def test_stream_api_key_empty_string_401(client, mock_engine, mock_key_manager):
    """
    GET /chat/stream ?api_key= (chaîne vide) → 401.

    F-01 : query param vide → falsy en Python → provided=None → 401.
    """
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": ""},
    )
    assert r.status_code == 401


@requires_fastapi
def test_chat_exception_no_detail_leak(client, mock_engine, mock_key_manager):
    """
    POST /chat : exception dans engine.process → 500 sans détail interne.

    F-04 : le message d'erreur HTTP 500 doit être générique —
    aucune information interne (chemin, modèle, message réseau) ne doit fuiter.
    """
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    # Simuler une exception dans engine.process
    api_module._state.engine.process.side_effect = RuntimeError(
        "Internal path /secret/data and model ollama:3.2"
    )
    r = client.post(
        "/chat",
        json={"message": "test"},
        headers=VALID_HEADERS,
    )
    assert r.status_code == 500
    body = r.json()
    # Le message d'erreur interne ne doit PAS figurer dans la réponse
    assert "Internal path" not in body.get("detail", "")
    assert "/secret" not in body.get("detail", "")
    assert "ollama:3.2" not in body.get("detail", "")
    # Un message générique doit être présent
    assert body.get("detail") == "Erreur lors du traitement."


@requires_fastapi
def test_stream_real_tokens(client, mock_engine, mock_key_manager):
    """GET /chat/stream : les tokens de process_stream apparaissent dans le SSE."""
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": TEST_API_KEY},
    )
    assert r.status_code == 200
    assert "Reponse" in r.text
    assert "test EVA" in r.text


@requires_fastapi
def test_stream_exception_no_detail_leak(client, mock_engine, mock_key_manager):
    """
    GET /chat/stream : exception dans engine.process → event:error sans détail interne.

    F-05 : le champ "message" de l'événement SSE error doit être générique.
    """
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    api_module._state.engine.process_stream.side_effect = RuntimeError(
        "Sensitive internal info: /home/user/.secrets"
    )
    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": TEST_API_KEY},
    )
    assert r.status_code == 200  # SSE retourne 200 même en cas d'erreur interne
    # L'info interne ne doit pas figurer dans le stream SSE
    assert "Sensitive internal info" not in r.text
    assert "/home/user" not in r.text
    # L'événement error doit être émis avec un message générique
    assert "event: error" in r.text
    assert "Erreur lors du traitement" in r.text


# --- Tests Phase 5(C) — /metrics + event:done TTFT ---


@requires_fastapi
def test_metrics_requires_auth_401(client, mock_key_manager):
    """GET /metrics sans cle API -> 401."""
    api_module._state.key_manager = mock_key_manager
    r = client.get("/metrics")
    assert r.status_code == 401


@requires_fastapi
def test_metrics_valid_auth_200(client, mock_key_manager):
    """GET /metrics avec cle valide -> 200 + structure JSON attendue."""
    from eva.api.metrics import MetricsCollector
    api_module._state.key_manager = mock_key_manager
    api_module._state.metrics_collector = MetricsCollector()

    r = client.get("/metrics", headers={"Authorization": f"Bearer {TEST_API_KEY}"})

    assert r.status_code == 200
    data = r.json()
    assert "uptime_s" in data
    assert "endpoints" in data
    assert "chat" in data["endpoints"]
    assert "chat_stream" in data["endpoints"]

    chat = data["endpoints"]["chat"]
    assert "requests" in chat
    assert "p50_ms" in chat
    assert "p95_ms" in chat

    stream = data["endpoints"]["chat_stream"]
    assert "p50_ttft_ms" in stream
    assert "p95_ttft_ms" in stream


@requires_fastapi
def test_metrics_503_when_not_initialized(client, mock_key_manager):
    """GET /metrics -> 503 si metrics_collector non initialise."""
    api_module._state.key_manager = mock_key_manager
    # metrics_collector reste None (reset_state)

    r = client.get("/metrics", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert r.status_code == 503


@requires_fastapi
def test_stream_done_contains_ttft(client, mock_engine, mock_key_manager):
    """event:done SSE contient ttft_ms et tokens quand streaming actif."""
    from eva.api.metrics import MetricsCollector
    api_module._state.engine = mock_engine
    api_module._state.key_manager = mock_key_manager
    api_module._state.metrics_collector = MetricsCollector()

    r = client.get(
        "/chat/stream",
        params={"message": "test", "api_key": TEST_API_KEY},
    )
    assert r.status_code == 200
    assert "event: done" in r.text

    # Extraire le payload de event:done
    import json as _json
    done_payload = None
    for line in r.text.splitlines():
        if line.startswith("data:") and "ok" in line:
            try:
                payload = _json.loads(line[5:].strip())
                if payload.get("ok") is True:
                    done_payload = payload
            except Exception:
                pass

    assert done_payload is not None
    assert "latency_ms" in done_payload
    assert "ok" in done_payload
    # ttft_ms et tokens sont presents si des tokens ont ete emis
    assert "ttft_ms" in done_payload
    assert "tokens" in done_payload
    assert done_payload["tokens"] > 0
