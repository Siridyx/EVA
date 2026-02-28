"""Tests unitaires pour EVAEngine (R-006)"""

import pytest
from eva.core.eva_engine import EVAEngine
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
    bus.clear()  # Clean state
    return bus


def test_engine_init(config, event_bus):
    """EVAEngine s'initialise correctement."""
    engine = EVAEngine(config, event_bus)
    
    assert engine.name == "EVAEngine"
    assert engine.pipeline_mode == "sequential"
    assert not engine.is_running
    assert not engine.pipeline_initialized


def test_engine_inherits_eva_component(config, event_bus):
    """EVAEngine hérite bien de EvaComponent."""
    engine = EVAEngine(config, event_bus)
    
    # A accès aux méthodes EvaComponent
    assert hasattr(engine, "start")
    assert hasattr(engine, "stop")
    assert hasattr(engine, "emit")
    assert hasattr(engine, "get_config")


def test_engine_start(config, event_bus):
    """start() démarre le moteur."""
    engine = EVAEngine(config, event_bus)
    
    engine.start()
    
    assert engine.is_running
    assert engine.pipeline_initialized


def test_engine_stop(config, event_bus):
    """stop() arrête le moteur."""
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    engine.stop()
    
    assert not engine.is_running
    assert not engine.pipeline_initialized


def test_engine_lifecycle_events(config, event_bus):
    """Lifecycle émet les bons événements."""
    events = []
    
    for evt in ["engine_initializing", "engine_starting", "engine_ready",
                "engine_running", "engine_stopping", "engine_stopped"]:
        event_bus.on(evt, lambda p, e=evt: events.append(e))
    
    engine = EVAEngine(config, event_bus)
    engine.start()
    engine.stop()
    
    assert "engine_initializing" in events
    assert "engine_starting" in events
    assert "engine_ready" in events
    assert "engine_running" in events
    assert "engine_stopping" in events
    assert "engine_stopped" in events


def test_engine_process_requires_running(config, event_bus):
    """process() nécessite que le moteur soit démarré."""
    engine = EVAEngine(config, event_bus)
    
    with pytest.raises(RuntimeError, match="not running"):
        engine.process("Hello")


def test_engine_process_stub_p0(config, event_bus):
    """process() retourne fallback si ConversationEngine absent."""
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    response = engine.process("Bonjour EVA")
    
    # P1 : fallback si pas configuré
    assert "not configured" in response
    
    engine.stop()


def test_engine_process_emits_message_received(config, event_bus):
    """process() émet message_received."""
    events = []
    event_bus.on("message_received", lambda p: events.append(p))
    
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    engine.process("Test")
    
    assert len(events) == 1
    assert events[0]["input_length"] == 4  # "Test"
    
    engine.stop()


def test_engine_status(config, event_bus):
    """status() retourne l'état complet."""
    engine = EVAEngine(config, event_bus)
    
    status = engine.status()
    
    assert status["name"] == "EVAEngine"
    assert status["running"] is False
    assert status["pipeline_mode"] == "sequential"
    assert "components" in status


def test_engine_status_after_start(config, event_bus):
    """status() reflète l'état après start()."""
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    status = engine.status()
    
    assert status["running"] is True
    assert status["pipeline_initialized"] is True


def test_engine_repr(config, event_bus):
    """__repr__ retourne représentation correcte."""
    engine = EVAEngine(config, event_bus)
    
    repr_str = repr(engine)
    
    assert "EVAEngine" in repr_str
    assert "stopped" in repr_str
    assert "sequential" in repr_str


def test_engine_auto_start_disabled_by_default(config, event_bus):
    """auto_start est False par défaut."""
    engine = EVAEngine(config, event_bus)
    
    # Ne doit pas auto-start
    assert not engine.is_running


def test_engine_idempotent_start(config, event_bus):
    """start() est idempotent."""
    engine = EVAEngine(config, event_bus)
    
    engine.start()
    engine.start()  # 2ème appel
    
    # Pas d'erreur, toujours running
    assert engine.is_running


def test_engine_idempotent_stop(config, event_bus):
    """stop() est idempotent."""
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    engine.stop()
    engine.stop()  # 2ème appel
    
    # Pas d'erreur, toujours stopped
    assert not engine.is_running


def test_engine_pipeline_mode_from_config(config, event_bus):
    """pipeline_mode vient de la config."""
    engine = EVAEngine(config, event_bus)
    
    # Depuis config.yaml
    assert engine.pipeline_mode == config.get("engine.pipeline_mode")


def test_engine_components_none_in_p0(config, event_bus):
    """En P0, les composants sont None."""
    engine = EVAEngine(config, event_bus)
    engine.start()
    
    status = engine.status()
    
    assert status["components"]["llm"] is False
    assert status["components"]["memory"] is False
    assert status["components"]["conversation"] is False


# --- P1 : ConversationEngine integration ---

def test_engine_set_conversation_engine(config, event_bus):
    """set_conversation_engine() configure le ConversationEngine."""
    from eva.conversation.conversation_engine import ConversationEngine
    from eva.memory.memory_manager import MemoryManager
    from eva.prompt.prompt_manager import PromptManager
    from eva.llm.providers.openai_provider import OpenAIProvider
    
    # Mock transport
    class MockTransport:
        def post(self, url, json, headers, timeout):
            return {"choices": [{"message": {"content": "Test reply"}}]}
    
    # Setup components
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test"
    
    memory = MemoryManager(config, event_bus)
    memory.start()
    
    prompt = PromptManager(config, event_bus)
    prompt.start()
    
    llm = OpenAIProvider(config, event_bus, transport=MockTransport())
    llm.start()
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    # Configure engine
    engine = EVAEngine(config, event_bus)
    engine.set_conversation_engine(conv)
    
    assert engine._conversation_engine is conv
    
    # Cleanup
    conv.stop()
    llm.stop()
    prompt.stop()
    memory.stop()

@pytest.mark.xfail(reason="DEBT-008: Prompts invalides")
def test_engine_process_with_conversation_engine(config, event_bus):
    """process() utilise ConversationEngine si configuré."""
    from eva.conversation.conversation_engine import ConversationEngine
    from eva.memory.memory_manager import MemoryManager
    from eva.prompt.prompt_manager import PromptManager
    from eva.llm.providers.openai_provider import OpenAIProvider
    
    # Mock transport
    class MockTransport:
        def post(self, url, json, headers, timeout):
            return {"choices": [{"message": {"content": "EVA response"}}]}
    
    # Setup components
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test"
    
    memory = MemoryManager(config, event_bus)
    memory.start()
    memory.clear()  # Clean
    
    prompt = PromptManager(config, event_bus)
    prompt.start()
    
    llm = OpenAIProvider(config, event_bus, transport=MockTransport())
    llm.start()
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    # Configure et start engine
    engine = EVAEngine(config, event_bus)
    engine.set_conversation_engine(conv)
    engine.start()
    
    # Process via ConversationEngine
    reply = engine.process("Hello EVA")
    
    assert reply == "EVA response"
    assert memory.message_count == 2  # user + assistant
    
    # Cleanup
    engine.stop()
    conv.stop()
    llm.stop()
    prompt.stop()
    memory.stop()


def test_engine_process_without_conversation_engine(config, event_bus):
    """process() retourne fallback si ConversationEngine absent."""
    engine = EVAEngine(config, event_bus)
    engine.start()

    reply = engine.process("Test")

    assert "not configured" in reply

    engine.stop()


# --- Tests process_stream() — Phase 5(A) ---


def test_process_stream_not_running(config, event_bus):
    """process_stream() leve RuntimeError si moteur non demarre."""
    engine = EVAEngine(config, event_bus)

    with pytest.raises(RuntimeError, match="not running"):
        list(engine.process_stream("test"))


def test_process_stream_without_conversation_engine(config, event_bus):
    """process_stream() yielde fallback si ConversationEngine absent."""
    engine = EVAEngine(config, event_bus)
    engine.start()

    tokens = list(engine.process_stream("Test"))

    engine.stop()

    assert len(tokens) == 1
    assert "not configured" in tokens[0]


def test_process_stream_delegates_to_conversation_engine(config, event_bus):
    """process_stream() delegue respond_stream() a ConversationEngine."""
    from unittest.mock import MagicMock

    engine = EVAEngine(config, event_bus)
    engine.start()

    mock_conv = MagicMock()
    mock_conv.respond_stream.return_value = iter(["Bonjour", " EVA"])
    engine.set_conversation_engine(mock_conv)

    tokens = list(engine.process_stream("test"))

    engine.stop()

    assert tokens == ["Bonjour", " EVA"]
    mock_conv.respond_stream.assert_called_once_with("test")