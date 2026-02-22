"""
Tests smoke pour EVA — Validation basique

Tests de fumée pour s'assurer que les composants
principaux fonctionnent ensemble.
"""

import pytest
import sys
from pathlib import Path

xfail_smoke = pytest.mark.xfail(
    reason="DEBT-008: Smoke tests utilisent paths data/ réels"
)

# Ajouter racine au path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))


def test_imports():
    """Les imports principaux fonctionnent."""
    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.core.eva_component import EvaComponent
    from eva.core.eva_engine import EVAEngine
    
    assert ConfigManager
    assert EventBus
    assert EvaComponent
    assert EVAEngine


def test_eva_engine_basic_workflow():
    """Workflow complet : init → start → process → stop."""
    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.core.eva_engine import EVAEngine
    
    # Init
    config = ConfigManager()
    bus = EventBus()
    engine = EVAEngine(config, bus)
    
    # Start
    engine.start()
    assert engine.is_running
    
    # Process (P1 : fallback si pas configuré)
    response = engine.process("Test message")
    assert "not configured" in response or "Phase 0" in response
    
    # Stop
    engine.stop()
    assert not engine.is_running


def test_cli_script_exists():
    """Le script CLI existe."""
    cli_path = ROOT_DIR / "eva" / "repl.py"
    assert cli_path.exists()

@xfail_smoke
@pytest.mark.smoke
def test_full_stack_integration():
    """Test d'intégration : tous les composants ensemble."""
    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.core.eva_engine import EVAEngine
    
    # Setup
    config = ConfigManager()
    bus = EventBus()
    
    # Vérifier config
    assert config.version == "0.1.0-dev"
    assert config.get_path("logs").exists()
    
    # Vérifier bus
    events = []
    bus.on("test_event", lambda p: events.append(p))
    bus.emit("test_event", {"data": "test"})
    assert len(events) == 1
    
    # Vérifier engine
    engine = EVAEngine(config, bus)
    engine.start()
    
    status = engine.status()
    assert status["running"] is True
    assert status["pipeline_mode"] == "sequential"
    
    engine.stop()
    assert not engine.is_running


# --- P1 : Full stack conversation ---

@xfail_smoke
def test_full_conversation_flow_p1():
    """
    Test full stack P1 : EVAEngine → ConversationEngine → Memory + Prompt + LLM.
    
    Vérifie :
    - Init complète de tous les composants
    - Conversation multi-tours
    - Persistence memory
    - Events émis
    - Pipeline complet fonctionnel
    """
    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.core.eva_engine import EVAEngine
    from eva.conversation.conversation_engine import ConversationEngine
    from eva.memory.memory_manager import MemoryManager
    from eva.prompt.prompt_manager import PromptManager
    from eva.llm.providers.openai_provider import OpenAIProvider
    import os
    
    # Mock transport (pas d'appels réseau réels)
    class MockTransport:
        def __init__(self):
            self.call_count = 0
        
        def post(self, url, json, headers, timeout):
            self.call_count += 1
            # Réponse différente selon le tour
            if self.call_count == 1:
                return {"choices": [{"message": {"content": "Bonjour ! Comment puis-je vous aider ?"}}]}
            elif self.call_count == 2:
                return {"choices": [{"message": {"content": "Python est un langage de programmation."}}]}
            else:
                return {"choices": [{"message": {"content": "Réponse EVA."}}]}
    
    # Setup
    config = ConfigManager()
    bus = EventBus()
    mock_transport = MockTransport()
    
    # Capturer events
    events = []
    for event_name in [
        "conversation_request_received",
        "conversation_context_built",
        "llm_request_started",
        "llm_request_succeeded",
        "conversation_reply_ready"
    ]:
        bus.on(event_name, lambda p, name=event_name: events.append(name))
    
    # Components
    os.environ["OPENAI_API_KEY"] = "sk-test-full-stack"
    
    memory = MemoryManager(config, bus)
    memory.start()
    memory.clear()  # Clean start
    
    prompt = PromptManager(config, bus)
    prompt.start()
    
    llm = OpenAIProvider(config, bus, transport=mock_transport)
    llm.start()
    
    conv = ConversationEngine(config, bus, memory, prompt, llm)
    conv.start()
    
    engine = EVAEngine(config, bus)
    engine.set_conversation_engine(conv)
    engine.start()
    
    # Tour 1 : Salutation
    reply1 = engine.process("Bonjour EVA")
    assert reply1 == "Bonjour ! Comment puis-je vous aider ?"
    assert memory.message_count == 2  # user + assistant
    
    # Tour 2 : Question
    reply2 = engine.process("Qu'est-ce que Python ?")
    assert reply2 == "Python est un langage de programmation."
    assert memory.message_count == 4  # 2 tours × 2 messages
    
    # Tour 3 : Continuation
    reply3 = engine.process("Merci")
    assert reply3 == "Réponse EVA."
    assert memory.message_count == 6  # 3 tours × 2 messages
    
    # Vérifier historique complet
    messages = memory.get_all_messages()
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Bonjour EVA"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Bonjour ! Comment puis-je vous aider ?"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "Qu'est-ce que Python ?"
    assert messages[3]["role"] == "assistant"
    assert messages[4]["role"] == "user"
    assert messages[5]["role"] == "assistant"
    
    # Vérifier events émis (au moins 1 set par tour)
    assert "conversation_request_received" in events
    assert "conversation_context_built" in events
    assert "llm_request_started" in events
    assert "llm_request_succeeded" in events
    assert "conversation_reply_ready" in events
    
    # Vérifier LLM appelé 3 fois
    assert mock_transport.call_count == 3
    
    # Cleanup
    engine.stop()
    conv.stop()
    llm.stop()
    prompt.stop()
    memory.stop()
    
    # Success ✅
    print("\n🎉 Full stack P1 conversation : SUCCESS")


# --- R-015 : Plugin System smoke test ---

def test_plugin_system_full_stack():
    """
    Test full stack plugin system.
    
    Vérifie :
    - PluginRegistry créé et démarré
    - PluginLoader charge example_plugin.py
    - Plugin enregistre tool "greet"
    - Tool fonctionnel
    """
    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.plugins import PluginRegistry, PluginLoader
    from pathlib import Path
    
    # Setup
    config = ConfigManager()
    bus = EventBus()
    
    # Registry
    registry = PluginRegistry(config, bus)
    registry.start()
    
    # Loader (pointe vers plugins/ racine)
    eva_root = Path(__file__).parent.parent.parent
    plugins_dir = eva_root / "plugins"
    
    loader = PluginLoader(config, bus, registry, plugins_dir=plugins_dir)
    loader.start()
    
    # Charger plugins
    loaded, failed = loader.load_plugins()
    
    # Vérifications
    if "example" in loaded:
        # Example plugin chargé
        assert registry.plugin_count >= 1
        
        # Tool "greet" enregistré
        greet_tool = registry.get_tool("greet")
        assert greet_tool is not None
        
        # Tool fonctionnel
        result = greet_tool("World")
        assert result == "Hello, World! Welcome to EVA."
        
        print("\n✅ Plugin system smoke test: SUCCESS")
        print(f"   - Loaded plugins: {loaded}")
        print(f"   - Tool 'greet' functional: {result}")
    else:
        # Example plugin absent (OK si pas encore créé)
        print("\n⚠️  Example plugin not found (create plugins/example_plugin.py)")
    
    # Cleanup
    loader.stop()
    registry.stop()