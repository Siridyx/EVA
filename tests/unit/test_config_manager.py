"""Tests unitaires pour ConfigManager"""

import pytest
import os
from pathlib import Path
from eva.core.config_manager import ConfigManager

os.environ["EVA_TEST_MODE"] = "1"


def test_config_manager_init():
    """ConfigManager s'initialise correctement."""
    config = ConfigManager()
    assert config.version == "0.1.0-dev"
    assert config.environment == "development"


def test_config_get_simple():
    """get() récupère une valeur simple."""
    config = ConfigManager()
    assert config.get("version") == "0.1.0-dev"


def test_config_get_nested():
    """get() récupère une valeur imbriquée."""
    config = ConfigManager()
    # Ancienne structure : llm.default_model
    # Ollama par défaut maintenant
    assert config.get("llm.models.default") == "llama3:8b"


def test_config_get_default():
    """get() retourne default si clé absente."""
    config = ConfigManager()
    assert config.get("unknown.key", "fallback") == "fallback"

@pytest.mark.skipif(
    os.environ.get("EVA_TEST_MODE") == "1",
    reason="Paths tests skip in test mode (tmp_path used)"
)

def test_config_get_path():
    """get_path() retourne un Path absolu."""
    config = ConfigManager()
    logs_path = config.get_path("logs")
    
    assert isinstance(logs_path, Path)
    assert logs_path.is_absolute()
    assert logs_path.exists()  # Créé automatiquement

@pytest.mark.skipif(
    os.environ.get("EVA_TEST_MODE") == "1",
    reason="Paths tests skip in test mode (tmp_path used)"
)

def test_config_paths_exist():
    """Tous les chemins data/ sont créés."""
    config = ConfigManager()
    
    for key in ["logs", "memory", "cache", "prompts", "dumps"]:
        path = config.get_path(key)
        assert path.exists(), f"Path {key} should exist"


@pytest.mark.parametrize("key,expected", [
    ("version", "0.1.0-dev"),
    ("environment", "development"),
    ("llm.default_provider", "ollama"),
    ("llm.models.default", "llama3:8b"),
])

def test_config_values(key, expected):
    """Valeurs de config correctes."""
    config = ConfigManager()
    assert config.get(key) == expected