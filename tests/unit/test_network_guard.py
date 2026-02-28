"""
Tests du network guard (R-045 — Test Hardening).

Vérifie que le guard (tests/conftest.py) :
- Bloque les connexions vers des hôtes externes (preuve de couverture)
- Autorise les hôtes loopback (127.0.0.1, localhost, ::1)
- Autorise "testserver" (pseudo-host FastAPI TestClient)

Ces tests constituent la "preuve" R-045 DoD :
  "Un appel réseau externe en test fait échouer immédiatement."

Standards : Python 3.9 strict — zéro import externe.
"""

from __future__ import annotations

import socket

import pytest


# ---------------------------------------------------------------------------
# Blocage — hôtes externes
# ---------------------------------------------------------------------------


def test_guard_blocks_external_hostname() -> None:
    """getaddrinfo vers un hostname externe lève OSError (guard actif)."""
    with pytest.raises(OSError, match="Network Guard"):
        socket.getaddrinfo("example.com", 80)


def test_guard_blocks_external_ip() -> None:
    """getaddrinfo vers une IP externe (8.8.8.8) est bloqué."""
    with pytest.raises(OSError, match="Network Guard"):
        socket.getaddrinfo("8.8.8.8", 53)


def test_guard_blocks_api_provider() -> None:
    """getaddrinfo vers un endpoint LLM cloud est bloqué."""
    with pytest.raises(OSError, match="Network Guard"):
        socket.getaddrinfo("api.openai.com", 443)


# ---------------------------------------------------------------------------
# Autorisé — loopback
# ---------------------------------------------------------------------------


def test_guard_allows_loopback_ip() -> None:
    """getaddrinfo vers 127.0.0.1 est autorisé (loopback)."""
    result = socket.getaddrinfo("127.0.0.1", 80)
    assert result  # liste non vide = résolution OK


def test_guard_allows_localhost() -> None:
    """getaddrinfo vers localhost est autorisé."""
    result = socket.getaddrinfo("localhost", 80)
    assert result


def test_guard_allows_testserver() -> None:
    """
    "testserver" est dans la liste blanche (FastAPI TestClient).

    TestClient (httpx + ASGITransport) ne fait pas de vraie connexion TCP,
    mais le host "testserver" doit passer le guard sans OSError.
    Si la résolution DNS échoue (hôte inconnu), l'erreur ne doit pas
    provenir du guard.
    """
    try:
        socket.getaddrinfo("testserver", 80)
    except OSError as exc:
        assert "Network Guard" not in str(exc), (
            f"Guard a bloqué 'testserver' alors qu'il est autorisé : {exc}"
        )


# ---------------------------------------------------------------------------
# Message d'erreur — contenu
# ---------------------------------------------------------------------------


def test_guard_error_message_mentions_mock() -> None:
    """Le message d'erreur guide vers la solution (utiliser des mocks)."""
    with pytest.raises(OSError) as exc_info:
        socket.getaddrinfo("external.example.com", 443)
    msg = str(exc_info.value)
    assert "Network Guard" in msg
    assert "mock" in msg.lower() or "Mock" in msg
