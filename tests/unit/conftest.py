"""
Pytest fixtures partagées pour tous les tests EVA.
"""

import pytest
import os
from pathlib import Path
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager


@pytest.fixture
def config(tmp_path):
    """
    Fixture ConfigManager avec isolation tmp_path.
    
    Utilise le vrai config.yaml du projet mais avec EVA_DATA_DIR isolé.
    """
    # Set EVA_DATA_DIR vers tmp pour isolation
    os.environ["EVA_DATA_DIR"] = str(tmp_path / "data")
    
    # Utiliser le vrai config.yaml du projet
    # Il est dans eva/ (3 niveaux au-dessus de tests/unit/)
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / "eva" / "config.yaml"
    
    # Créer ConfigManager
    config = ConfigManager(str(config_file))
    
    return config


@pytest.fixture
def event_bus():
    """
    Fixture EventBus propre pour chaque test.
    """
    return EventBus()


@pytest.fixture
def memory(tmp_path, config, event_bus):
    """
    Fixture MemoryManager pour tests.
    """
    mem = MemoryManager(config, event_bus)
    mem.start()
    yield mem
    mem.stop()


@pytest.fixture
def prompt(tmp_path, config, event_bus):
    """
    Fixture PromptManager pour tests.
    """
    pm = PromptManager(config, event_bus)
    pm.start()
    yield pm
    pm.stop()