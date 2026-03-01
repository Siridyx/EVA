"""
Tests de l'interface web légère (R-032) — 4 tests essentiels.

Stratégie :
- Importer eva.web.app enregistre GET / sur l'app FastAPI existante
- TestClient Starlette (synchrone, sans lifespan — pas d'init EVA réelle)
- 4 tests couvrant la route web, le contenu HTML et le flag CLI

Standards :
- Python 3.9 strict
- Pas d'accès réseau
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import conditionnel : fastapi requis
# ---------------------------------------------------------------------------

try:
    # L'import de eva.web.app enregistre GET / sur l'app FastAPI (side-effect voulu)
    import eva.web.app  # noqa: F401
    from fastapi.testclient import TestClient
    from eva.api.app import app

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

requires_fastapi = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="fastapi non installé — pip install 'fastapi[standard]'",
)


# ---------------------------------------------------------------------------
# Fixture client
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """TestClient FastAPI SANS lifespan (pas d'init EVA réelle)."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 4 tests essentiels
# ---------------------------------------------------------------------------


@requires_fastapi
def test_web_index_ok(client):
    """GET / → 200 avec réponse HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@requires_fastapi
def test_web_has_chat_input(client):
    """La page HTML contient le champ de saisie du chat."""
    response = client.get("/")
    assert "msg-input" in response.text


@requires_fastapi
def test_cli_has_web_flag():
    """--web est présent dans eva/cli.py."""
    import eva.cli

    source = Path(eva.cli.__file__).read_text(encoding="utf-8")
    assert "--web" in source


@requires_fastapi
def test_web_references_chat_api(client):
    """La page HTML référence l'endpoint /chat (appels fetch)."""
    response = client.get("/")
    assert "/chat" in response.text


@requires_fastapi
def test_web_references_metrics(client):
    """La page HTML reference /metrics (polling perf Phase 5(D))."""
    response = client.get("/")
    assert "/metrics" in response.text


@requires_fastapi
def test_web_has_perf_badge(client):
    """La page HTML contient le badge perf (header Phase 5(D))."""
    response = client.get("/")
    assert "perf-badge" in response.text


@requires_fastapi
def test_web_has_login_overlay(client):
    """La page HTML contient le login overlay (Phase 6(A))."""
    response = client.get("/")
    assert "login-overlay" in response.text


@requires_fastapi
def test_web_no_api_key_injected(client):
    """La page HTML ne contient pas le placeholder __API_KEY__ (Phase 6(A))."""
    response = client.get("/")
    assert "__API_KEY__" not in response.text
