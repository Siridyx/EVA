"""
Conftest racine EVA — R-045 Test Hardening.

Contient :
- Network guard (autouse, session) : bloque tout appel réseau externe,
  autorise uniquement le loopback (127.0.0.1 / localhost / ::1).
- Auto-marking : unit / integration / smoke selon le chemin du test.
  Aucune annotation @pytest.mark.xxx n'est nécessaire dans les fichiers.

Commandes utiles :
    pytest -m unit          # tests rapides (dev local)
    pytest -m integration   # tests avec vraies dépendances externes
    pytest -m smoke         # smoke tests
    pytest                  # tout (CI)
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Iterator, List

import pytest

# ---------------------------------------------------------------------------
# Network guard — configuration
# ---------------------------------------------------------------------------

# Hôtes autorisés en tests (loopback + pseudo-host FastAPI TestClient)
_ALLOWED_HOSTS: frozenset = frozenset(
    {"127.0.0.1", "localhost", "::1", "0.0.0.0", "testserver"}
)

_GUARD_MESSAGE = (
    "[EVA Network Guard] Connexion réseau externe bloquée vers {host!r}. "
    "Les tests unitaires doivent utiliser des mocks (MockTransport, MagicMock, etc.). "
    "Pour un test nécessitant un service réel, placez-le dans tests/integration/."
)

# Sauvegarder la fonction originale au niveau module (avant tout patch)
_orig_getaddrinfo = socket.getaddrinfo


def _guarded_getaddrinfo(  # type: ignore[override]
    host: str, port, *args, **kwargs
):
    """
    Remplacement de socket.getaddrinfo — bloque les hôtes non-loopback.

    Point d'entrée unique pour toute résolution DNS/IP en Python :
    couvre requests, httpx, urllib, asyncio.get_event_loop().create_connection…
    """
    if host not in _ALLOWED_HOSTS:
        raise OSError(_GUARD_MESSAGE.format(host=host))
    return _orig_getaddrinfo(host, port, *args, **kwargs)


@pytest.fixture(autouse=True, scope="session")
def network_guard() -> Iterator[None]:
    """
    Network guard — autouse, session-scoped.

    Active le blocage réseau pour toute la session de tests.
    Aucun test unitaire ne peut émettre une requête vers l'extérieur.

    Autorisé  : 127.0.0.1, localhost, ::1, 0.0.0.0, testserver
    Bloqué    : tout autre hôte (ex: example.com, 8.8.8.8, api.openai.com…)
    """
    socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
    yield
    socket.getaddrinfo = _orig_getaddrinfo  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Auto-marking — unit / integration / smoke
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: List[pytest.Item]) -> None:
    """
    Hook pytest — marque automatiquement les tests selon leur chemin.

    Règle :
        tests/unit/**        → marker "unit"
        tests/integration/** → marker "integration"
        tests/smoke/**       → marker "smoke"

    Avantage : aucune décoration manuelle n'est nécessaire dans les fichiers.
    Les markers déclarés dans pyproject.toml [tool.pytest.ini_options] restent
    la source de vérité pour --strict-markers.
    """
    for item in items:
        parts = set(Path(item.fspath).parts)
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in parts:
            item.add_marker(pytest.mark.integration)
        elif "smoke" in parts:
            item.add_marker(pytest.mark.smoke)
