"""
Tests du boot output CLI EVA -- Phase 6(D.1) hardening.

Verifie que :
- eva --api et eva --web n'affichent pas d'URL cliquable /docs ni /redoc au demarrage
- eva --print-api-urls affiche /docs et /redoc (commande dev explicite)

Strategie : mock uvicorn.run pour eviter de lancer un vrai serveur.
Les tests verifient l'absence d'URL HTTP completes (http://host:port/docs),
pas l'absence de la chaine "/docs" (la note l'evoque par design).
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from eva.cli import _print_api_urls

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOST = "127.0.0.1"
_PORT = 8000


def _docs_url() -> str:
    return f"http://{_HOST}:{_PORT}/docs"


def _redoc_url() -> str:
    return f"http://{_HOST}:{_PORT}/redoc"


def _run_api_main(**kwargs) -> str:
    """Lance api.main() avec uvicorn mocke et capture stdout."""
    try:
        from eva.api.app import main as api_main
    except ImportError:
        pytest.skip("fastapi non installe")

    buf = io.StringIO()
    # ConfigManager peut echouer en test (pas de config.yaml) -> _api_key=None, OK.
    # uvicorn.run mocke pour ne pas demarrer de vrai serveur.
    with patch("uvicorn.run"):
        with patch("sys.stdout", buf):
            api_main(**kwargs)
    return buf.getvalue()


def _run_web_main(**kwargs) -> str:
    """Lance web.main() avec uvicorn mocke et capture stdout."""
    try:
        import eva.web.app  # enregistre GET /
        from eva.web.app import main as web_main
    except ImportError:
        pytest.skip("fastapi non installe")

    buf = io.StringIO()
    with patch("uvicorn.run"):
        with patch("sys.stdout", buf):
            web_main(**kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests eva/api/app.py main() boot output
# ---------------------------------------------------------------------------


def test_api_boot_no_docs_url():
    """`eva --api` ne doit pas afficher l'URL cliquable /docs au demarrage."""
    output = _run_api_main()
    assert _docs_url() not in output, (
        f"URL /docs presente dans le boot output : {output!r}"
    )


def test_api_boot_no_redoc_url():
    """`eva --api` ne doit pas afficher l'URL cliquable /redoc au demarrage."""
    output = _run_api_main()
    assert _redoc_url() not in output


def test_api_boot_contains_base_url():
    """`eva --api` affiche l'URL de base."""
    output = _run_api_main()
    assert f"{_HOST}:{_PORT}" in output


def test_api_boot_contains_openapi():
    """`eva --api` affiche l'URL openapi.json."""
    output = _run_api_main()
    assert "/openapi.json" in output


def test_api_boot_contains_dev_note():
    """`eva --api` affiche la note dev-only sur /docs."""
    output = _run_api_main()
    # La note doit mentionner "dev" ou "development"
    assert "dev" in output.lower()


# ---------------------------------------------------------------------------
# Tests eva/web/app.py main() boot output
# ---------------------------------------------------------------------------


def test_web_boot_no_docs_url():
    """`eva --web` ne doit pas afficher l'URL cliquable /docs au demarrage."""
    output = _run_web_main()
    assert _docs_url() not in output, (
        f"URL /docs presente dans le boot output web : {output!r}"
    )


def test_web_boot_no_redoc_url():
    """`eva --web` ne doit pas afficher l'URL cliquable /redoc au demarrage."""
    output = _run_web_main()
    assert _redoc_url() not in output


def test_web_boot_contains_openapi():
    """`eva --web` affiche l'URL openapi.json."""
    output = _run_web_main()
    assert "/openapi.json" in output


def test_web_boot_contains_dev_note():
    """`eva --web` affiche la note dev-only."""
    output = _run_web_main()
    assert "dev" in output.lower()


# ---------------------------------------------------------------------------
# Tests _print_api_urls (commande dev explicite)
# ---------------------------------------------------------------------------


def test_print_api_urls_contains_docs(capsys):
    """eva --print-api-urls affiche /docs."""
    _print_api_urls()
    out = capsys.readouterr().out
    assert "/docs" in out


def test_print_api_urls_contains_redoc(capsys):
    """eva --print-api-urls affiche /redoc."""
    _print_api_urls()
    out = capsys.readouterr().out
    assert "/redoc" in out


def test_print_api_urls_contains_openapi(capsys):
    """eva --print-api-urls affiche /openapi.json."""
    _print_api_urls()
    out = capsys.readouterr().out
    assert "/openapi.json" in out


def test_print_api_urls_returns_zero():
    """_print_api_urls retourne 0."""
    assert _print_api_urls() == 0


def test_print_api_urls_contains_warning(capsys):
    """eva --print-api-urls affiche un avertissement dev-only."""
    _print_api_urls()
    out = capsys.readouterr().out
    assert "warning" in out.lower() or "dev" in out.lower()
