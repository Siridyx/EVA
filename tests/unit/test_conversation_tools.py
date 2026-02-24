"""Tests integration ConversationEngine + Tools"""

import pytest
import json
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager
from eva.conversation.conversation_engine import ConversationEngine
from eva.tools import tool, ToolRegistry, ToolExecutor

xfail_invalid_prompt = pytest.mark.xfail(
    reason="DEBT-008: Prompts invalides"
)

class MockLLM:
    """Mock LLM pour tests."""
    
    def __init__(self):
        self.responses = []
        self.call_count = 0
    
    def complete(self, messages, profile="default", tools=None):
        """Retourne réponses pré-définies."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "No more responses"
    
    def start(self):
        pass
    
    def stop(self):
        pass
    
    @property
    def is_running(self):
        return True


@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def memory(config, event_bus):
    m = MemoryManager(config, event_bus)
    m.start()
    yield m
    m.stop()


@pytest.fixture
def prompt(config, event_bus):
    p = PromptManager(config, event_bus)
    p.start()
    yield p
    p.stop()


@pytest.fixture
def registry(config, event_bus):
    r = ToolRegistry(config, event_bus)
    r.start()
    yield r
    r.stop()


@pytest.fixture
def executor(config, event_bus, registry):
    e = ToolExecutor(config, event_bus, registry)
    e.start()
    yield e
    e.stop()


def test_conversation_detect_tool_call(config, event_bus, memory, prompt):
    """ConversationEngine détecte tool call JSON."""
    mock_llm = MockLLM()
    
    conv = ConversationEngine(config, event_bus, memory, prompt, mock_llm)
    conv.start()
    
    # JSON tool call
    tool_call_json = '{"action":"tool_call","tool_name":"get_time","arguments":{"city":"Tokyo"}}'
    
    result = conv._detect_tool_call(tool_call_json)
    
    assert result is not None
    assert result["tool_name"] == "get_time"
    assert result["arguments"]["city"] == "Tokyo"
    
    conv.stop()


def test_conversation_detect_normal_response(config, event_bus, memory, prompt):
    """ConversationEngine ne détecte pas tool dans réponse normale."""
    mock_llm = MockLLM()
    
    conv = ConversationEngine(config, event_bus, memory, prompt, mock_llm)
    conv.start()
    
    # Réponse normale
    normal = "Il fait beau aujourd'hui"
    
    result = conv._detect_tool_call(normal)
    
    assert result is None
    
    conv.stop()


def test_conversation_with_tool_execution(config, event_bus, memory, prompt, registry, executor):
    """ConversationEngine exécute tool et rappelle LLM."""
    # Enregistrer tool
    @tool(
        name="get_time",
        description="Get time in city",
        parameters={"city": {"type": "string"}}
    )
    def get_time(city: str) -> dict:
        return {"city": city, "time": "15:30"}
    
    registry.register(get_time.tool_definition)
    
    # Mock LLM avec 2 réponses
    mock_llm = MockLLM()
    mock_llm.responses = [
        '{"action":"tool_call","tool_name":"get_time","arguments":{"city":"Tokyo"}}',  # 1er appel
        "Il est 15:30 à Tokyo"  # 2e appel après tool
    ]
    
    # ConversationEngine avec executor
    conv = ConversationEngine(config, event_bus, memory, prompt, mock_llm, executor)
    conv.start()
    
    # Conversation
    response = conv.respond("Quelle heure à Tokyo ?")
    
    assert response == "Il est 15:30 à Tokyo"
    assert mock_llm.call_count == 2  # LLM appelé 2 fois
    
    conv.stop()


def test_conversation_without_tool_executor(config, event_bus, memory, prompt):
    """ConversationEngine sans executor ignore tool calls."""
    mock_llm = MockLLM()
    mock_llm.responses = [
        '{"action":"tool_call","tool_name":"test","arguments":{}}'
    ]
    
    # Sans executor
    conv = ConversationEngine(config, event_bus, memory, prompt, mock_llm, tool_executor=None)
    conv.start()
    
    response = conv.respond("Test")
    
    # Retourne le JSON brut (pas exécuté)
    assert "tool_call" in response
    
    conv.stop()