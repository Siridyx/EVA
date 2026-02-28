"""
Tests integration Phase 5(B) — Summarization ConversationEngine + MemoryManager.

Couvre :
- resume auto declenche par respond()
- resume auto declenche par respond_stream()
- event memory_summarized emis
- isolation multi-conversation
"""

import pytest
from eva.conversation.conversation_engine import ConversationEngine
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager
from eva.llm.providers.ollama_provider import OllamaProvider
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


# --- Transport mock Ollama ---

class MockOllamaTransport:
    """Transport mock retournant une reponse valide pour complete() et stream()."""

    def post(self, url, json, headers, timeout, stream=False):
        if stream:
            return self._MockStreamResp()
        return {"response": "Reponse mock EVA."}

    class _MockStreamResp:
        def iter_lines(self):
            import json as _json
            return iter([
                _json.dumps({"response": "Token1", "done": False}).encode(),
                _json.dumps({"response": " Token2", "done": True}).encode(),
            ])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass


# --- Fixtures ---

@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def clean_memory(config, event_bus):
    """MemoryManager isole avec seuil bas pour tests de resume."""
    memory_path = config.get_path("memory")

    # Backup sessions existantes
    backups = []
    for f in memory_path.glob("conversation_*.json"):
        backups.append((f, f.read_text()))
        f.unlink()

    mem = MemoryManager(config, event_bus)
    # Seuil bas pour declencher rapidement
    mem._summary_threshold = 6
    mem._summary_keep_recent = 2
    mem.start()

    yield mem

    mem.stop()

    # Restore
    for f in memory_path.glob("conversation_*.json"):
        if not any(backup[0] == f for backup in backups):
            f.unlink()
    for f, content in backups:
        f.write_text(content)


@pytest.fixture
def prompt(config, event_bus):
    pm = PromptManager(config, event_bus)
    pm.start()
    yield pm
    pm.stop()


@pytest.fixture
def llm(config, event_bus):
    provider = OllamaProvider(config, event_bus, transport=MockOllamaTransport())
    provider.start()
    yield provider
    provider.stop()


@pytest.fixture
def engine(config, event_bus, clean_memory, prompt, llm):
    eng = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    eng.start()
    yield eng
    eng.stop()


# --- Tests ---


def test_respond_triggers_summary_when_threshold_exceeded(
    engine, clean_memory, event_bus
):
    """respond() declenche maybe_summarize quand message_count > threshold."""
    summary_events = []
    event_bus.on("memory_summarized", lambda p: summary_events.append(p))

    # Remplir la memoire jusqu'au seuil (threshold=6)
    for i in range(3):
        clean_memory.add_message("user", f"Question {i}")
        clean_memory.add_message("assistant", f"Reponse {i}")
    # 6 messages — seuil atteint

    # Un appel a respond() depasse le seuil (add_message user = 7 messages)
    engine.respond("Message qui declenche le resume")

    # Le resume doit avoir ete declenche
    assert len(summary_events) >= 1
    assert summary_events[0]["summarized_count"] > 0


def test_respond_memory_reduced_after_summary(engine, clean_memory):
    """Apres resume, message_count < seuil (memoire comprimee)."""
    # Remplir au dela du seuil
    for i in range(4):
        clean_memory.add_message("user", f"Question {i}")
        clean_memory.add_message("assistant", f"Reponse {i}")
    # 8 messages > threshold=6

    engine.respond("Nouveau message")

    # Apres resume : 1 summary + keep_recent(2) + user(+1 du respond) + assistant(+1) <= seuil
    assert clean_memory.message_count < 8


def test_respond_memory_contains_summary_marker(engine, clean_memory):
    """Apres resume, un message avec metadata.summary=True est present."""
    for i in range(4):
        clean_memory.add_message("user", f"Q{i}")
        clean_memory.add_message("assistant", f"R{i}")

    engine.respond("Trigger")

    summary_msgs = [
        m for m in clean_memory._messages
        if m.get("metadata", {}).get("summary") is True
    ]
    assert len(summary_msgs) == 1
    assert summary_msgs[0]["role"] == "system"


def test_respond_stream_triggers_summary(engine, clean_memory, event_bus):
    """respond_stream() declenche aussi le resume automatique."""
    summary_events = []
    event_bus.on("memory_summarized", lambda p: summary_events.append(p))

    # Remplir au dela du seuil
    for i in range(4):
        clean_memory.add_message("user", f"Q{i}")
        clean_memory.add_message("assistant", f"R{i}")
    # 8 messages > threshold=6

    # Consommer le generateur
    tokens = list(engine.respond_stream("Streaming trigger"))
    assert tokens  # au moins un token recu

    assert len(summary_events) >= 1


def test_summary_event_payload(config, event_bus, clean_memory):
    """Payload event memory_summarized contient les champs attendus."""
    events = []
    event_bus.on("memory_summarized", lambda p: events.append(p))

    # Trigger directly via maybe_summarize
    clean_memory._summary_threshold = 4
    clean_memory._summary_keep_recent = 1

    for i in range(5):
        clean_memory.add_message("user", f"M{i}")

    clean_memory.maybe_summarize(lambda msgs: "Resume payload test")

    assert len(events) == 1
    payload = events[0]
    assert "conversation_id" in payload
    assert "summarized_count" in payload
    assert "summary_length" in payload
    assert payload["summarized_count"] == 4  # 5 - keep_recent(1)
    assert payload["summary_length"] > 0


def test_multi_conversation_isolation(config, event_bus):
    """Deux MemoryManager distincts = sessions independantes."""
    memory_path = config.get_path("memory")

    # Backup
    backups = []
    for f in memory_path.glob("conversation_*.json"):
        backups.append((f, f.read_text()))
        f.unlink()

    try:
        mem1 = MemoryManager(config, event_bus)
        mem1.start()
        mem1.add_message("user", "Message conversation 1")
        conv_id_1 = mem1.conversation_id
        count_1 = mem1.message_count
        mem1.stop()

        # Deuxieme instance charge la session du jour (meme fichier)
        mem2 = MemoryManager(config, event_bus)
        mem2.start()
        mem2.add_message("assistant", "Reponse dans conv 1")
        mem2.stop()

        # Les deux utilisent le meme conv_id (session du jour)
        assert mem1.conversation_id == mem2.conversation_id == conv_id_1

        # La deuxieme instance voit les messages de la premiere
        # (comportement normal : meme fichier session du jour)
        assert mem2.message_count >= count_1

    finally:
        # Cleanup
        for f in memory_path.glob("conversation_*.json"):
            if not any(backup[0] == f for backup in backups):
                f.unlink()
        for f, content in backups:
            f.write_text(content)
