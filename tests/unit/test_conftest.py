"""Configuration globale pytest pour EVA."""

from pathlib import Path


def pytest_configure(config):
    """Configure pytest avec markers personnalisés."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (no network, fast)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (network allowed, slower)"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests (full stack)"
    )


def pytest_fixture_setup(fixturedef, request):
    """Hook appelé avant chaque fixture."""
    pass


import pytest
import os


@pytest.fixture(autouse=True)
def eva_test_mode(tmp_path, monkeypatch):
    """
    Configure EVA en mode test (isolation complète).
    
    - tmp_path pour tous les I/O
    - Timeouts courts
    - Pas de réseau (Step 3)
    
    Appliqué automatiquement à tous les tests.
    """
    # Data root isolé
    data_root = tmp_path / "eva_data"
    data_root.mkdir()
    
    monkeypatch.setenv("EVA_DATA_DIR", str(data_root))
    
    # Mode test
    monkeypatch.setenv("EVA_TEST_MODE", "1")
    
    # Créer structure data/
    for subdir in ["logs", "memory", "cache", "prompts", "dumps"]:
        (data_root / subdir).mkdir(parents=True, exist_ok=True)
    
    yield data_root


@pytest.fixture(autouse=True)
def block_network(request):
    """
    Bloque tout accès réseau en tests unitaires.
    
    Exception :
        - Tests dans tests/smoke/ (integration)
    
    Note : Actuellement désactivé car MockTransport trigger le guard.
    TODO (DEBT-004): Implémenter guard plus fin.
    """
    # Autoriser réseau dans tests smoke/integration
    if "smoke" in str(request.fspath):
        return
    
    # TODO: Guard réseau plus fin qui ne bloque pas MockTransport
    # Pour l'instant, on s'appuie sur MockTransport pour éviter réseau
    pass