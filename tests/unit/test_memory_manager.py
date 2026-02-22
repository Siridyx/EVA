"""Tests unitaires pour MemoryManager (R-011)"""

import pytest
import json
from pathlib import Path
from eva.memory.memory_manager import MemoryManager
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


@pytest.fixture
def config():
    """Fixture ConfigManager."""
    return ConfigManager()


@pytest.fixture
def event_bus():
    """Fixture EventBus."""
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def clean_memory(config):
    """Fixture pour nettoyer les fichiers de session."""
    memory_path = config.get_path("memory")
    
    # Backup et nettoyage
    backups = []
    for f in memory_path.glob("conversation_*.json"):
        backups.append((f, f.read_text()))
        f.unlink()
    
    yield memory_path
    
    # Restore
    for f, content in backups:
        f.write_text(content)
    
    # Cleanup nouveaux fichiers
    for f in memory_path.glob("conversation_*.json"):
        if not any(backup[0] == f for backup in backups):
            f.unlink()


def test_memory_manager_init(config, event_bus):
    """MemoryManager s'initialise correctement."""
    memory = MemoryManager(config, event_bus)
    
    assert memory.name == "MemoryManager"
    assert memory.context_window == 10
    assert memory.message_count == 0
    assert not memory.is_running


def test_memory_manager_start_creates_session(config, event_bus, clean_memory):
    """start() crée une nouvelle session."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    assert memory.is_running
    assert memory.conversation_id is not None
    assert memory.message_count == 0
    
    # Fichier créé
    session_files = list(clean_memory.glob("conversation_*.json"))
    assert len(session_files) == 1
    
    memory.stop()


def test_memory_manager_session_file_format(config, event_bus, clean_memory):
    """Session file a le bon format."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    session_file = list(clean_memory.glob("conversation_*.json"))[0]
    
    with open(session_file, 'r') as f:
        data = json.load(f)
    
    assert data["schema_version"] == 1
    assert "conversation_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "messages" in data
    assert isinstance(data["messages"], list)
    
    memory.stop()


def test_memory_manager_add_message(config, event_bus, clean_memory):
    """add_message() ajoute correctement."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    memory.add_message("user", "Bonjour")
    
    assert memory.message_count == 1
    
    messages = memory.get_all_messages()
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Bonjour"
    assert "timestamp" in messages[0]
    
    memory.stop()


def test_memory_manager_add_multiple_messages(config, event_bus, clean_memory):
    """add_message() multiples messages."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    memory.add_message("user", "Question 1")
    memory.add_message("assistant", "Réponse 1")
    memory.add_message("user", "Question 2")
    
    assert memory.message_count == 3
    
    memory.stop()


def test_memory_manager_invalid_role(config, event_bus, clean_memory):
    """add_message() rejette rôle invalide."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    with pytest.raises(ValueError, match="Invalid role"):
        memory.add_message("invalid", "message")
    
    memory.stop()


def test_memory_manager_add_before_start(config, event_bus):
    """add_message() avant start() raise."""
    memory = MemoryManager(config, event_bus)
    
    with pytest.raises(RuntimeError, match="not started"):
        memory.add_message("user", "message")


def test_memory_manager_get_context_window(config, event_bus, clean_memory):
    """get_context() retourne N derniers messages."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    # Ajouter 15 messages
    for i in range(15):
        memory.add_message("user", f"Message {i}")
    
    # Context window = 10 par défaut
    context = memory.get_context()
    
    assert len(context) == 10
    assert context[0]["content"] == "Message 5"  # 15 - 10 + 0
    assert context[-1]["content"] == "Message 14"
    
    memory.stop()


def test_memory_manager_get_context_custom_window(config, event_bus, clean_memory):
    """get_context(window=N) personnalisé."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    for i in range(10):
        memory.add_message("user", f"Message {i}")
    
    context = memory.get_context(window=3)
    
    assert len(context) == 3
    assert context[0]["content"] == "Message 7"
    
    memory.stop()


def test_memory_manager_trim_max_messages(config, event_bus, clean_memory):
    """Messages trimés si dépassent max_messages."""
    memory = MemoryManager(config, event_bus)
    # max_messages = 100 par défaut
    
    memory.start()
    
    # Ajouter 105 messages
    for i in range(105):
        memory.add_message("user", f"Message {i}")
    
    # Seulement 100 conservés
    assert memory.message_count == 100
    
    # Les 5 premiers supprimés
    messages = memory.get_all_messages()
    assert messages[0]["content"] == "Message 5"
    
    memory.stop()


def test_memory_manager_persistence(config, event_bus, clean_memory):
    """Session persiste entre start/stop."""
    memory1 = MemoryManager(config, event_bus)
    memory1.start()
    
    memory1.add_message("user", "Test persistence")
    conv_id1 = memory1.conversation_id
    
    memory1.stop()
    
    # Charger nouvelle instance
    memory2 = MemoryManager(config, event_bus)
    memory2.start()
    
    assert memory2.conversation_id == conv_id1
    assert memory2.message_count == 1
    assert memory2.get_all_messages()[0]["content"] == "Test persistence"
    
    memory2.stop()


def test_memory_manager_clear(config, event_bus, clean_memory):
    """clear() efface l'historique."""
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    memory.add_message("user", "Message 1")
    memory.add_message("user", "Message 2")
    
    old_conv_id = memory.conversation_id
    
    memory.clear()
    
    assert memory.conversation_id != old_conv_id
    assert memory.message_count == 0
    
    memory.stop()


def test_memory_manager_emits_events(config, event_bus, clean_memory):
    """Events émis correctement."""
    events = []
    
    for evt in ["memory_session_created", "memory_message_added", "memory_session_saved"]:
        event_bus.on(evt, lambda p, e=evt: events.append(e))
    
    memory = MemoryManager(config, event_bus)
    memory.start()
    memory.add_message("user", "Test")
    memory.stop()
    
    assert "memory_session_created" in events
    assert "memory_message_added" in events
    assert "memory_session_saved" in events


def test_memory_manager_repr(config, event_bus, clean_memory):
    """__repr__ retourne représentation correcte."""
    memory = MemoryManager(config, event_bus)
    
    repr_str = repr(memory)
    assert "MemoryManager" in repr_str
    assert "stopped" in repr_str
    
    memory.start()
    repr_str = repr(memory)
    assert "running" in repr_str
    
    memory.stop()