"""Tests pour Tools (ToolDefinition, Registry, Executor)"""

import pytest
from eva.tools.tool_definition import ToolDefinition

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.tools.tool_registry import ToolRegistry

from eva.tools.decorator import tool, is_tool, get_tool_definition

from eva.tools.tool_executor import ToolExecutor

# --- ToolDefinition Tests ---

def test_tool_definition_creation():
    """ToolDefinition peut être créé."""
    def dummy_func():
        return "test"
    
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        function=dummy_func,
        parameters={"arg1": {"type": "string"}},
        returns="string"
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.function == dummy_func
    assert "arg1" in tool.parameters


def test_tool_definition_requires_name():
    """ToolDefinition requiert un name."""
    with pytest.raises(ValueError, match="name cannot be empty"):
        ToolDefinition(
            name="",
            description="Test",
            function=lambda: None
        )


def test_tool_definition_requires_description():
    """ToolDefinition requiert une description."""
    with pytest.raises(ValueError, match="description cannot be empty"):
        ToolDefinition(
            name="test",
            description="",
            function=lambda: None
        )


def test_tool_definition_requires_callable():
    """ToolDefinition requiert une fonction callable."""
    with pytest.raises(ValueError, match="must be callable"):
        ToolDefinition(
            name="test",
            description="Test",
            function="not_a_function"
        )


def test_tool_definition_name_validation():
    """ToolDefinition valide le format du name."""
    with pytest.raises(ValueError, match="must be alphanumeric"):
        ToolDefinition(
            name="invalid-name",  # tiret non autorisé
            description="Test",
            function=lambda: None
        )


def test_tool_definition_validate_arguments_required():
    """validate_arguments vérifie paramètres requis."""
    tool = ToolDefinition(
        name="test",
        description="Test",
        function=lambda x: x,
        parameters={
            "city": {"type": "string", "required": True}
        }
    )
    
    # Missing required param
    with pytest.raises(ValueError, match="Missing required parameter"):
        tool.validate_arguments({})


def test_tool_definition_validate_arguments_type():
    """validate_arguments vérifie types."""
    tool = ToolDefinition(
        name="test",
        description="Test",
        function=lambda x: x,
        parameters={
            "count": {"type": "integer"}
        }
    )
    
    # Wrong type
    with pytest.raises(ValueError, match="must be integer"):
        tool.validate_arguments({"count": "not_an_int"})


def test_tool_definition_validate_arguments_unknown():
    """validate_arguments rejette paramètres inconnus."""
    tool = ToolDefinition(
        name="test",
        description="Test",
        function=lambda: None,
        parameters={}
    )
    
    with pytest.raises(ValueError, match="Unknown parameter"):
        tool.validate_arguments({"unknown": "value"})


def test_tool_definition_to_dict():
    """to_dict() retourne dict sans function."""
    tool = ToolDefinition(
        name="test",
        description="Test tool",
        function=lambda: None,
        parameters={"arg": {"type": "string"}}
    )
    
    d = tool.to_dict()
    
    assert d["name"] == "test"
    assert d["description"] == "Test tool"
    assert "function" not in d  # Pas serializable
    assert "arg" in d["parameters"]


def test_tool_definition_repr():
    """__repr__ est lisible."""
    tool = ToolDefinition(
        name="my_tool",
        description="Test",
        function=lambda: None,
        parameters={"a": {"type": "string"}, "b": {"type": "integer"}}
    )
    
    repr_str = repr(tool)
    
    assert "my_tool" in repr_str
    assert "a" in repr_str or "b" in repr_str

# --- ToolRegistry Tests ---

@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def registry(config, event_bus):
    reg = ToolRegistry(config, event_bus)
    reg.start()
    yield reg
    reg.stop()


def test_tool_registry_creation(config, event_bus):
    """ToolRegistry peut être créé."""
    registry = ToolRegistry(config, event_bus)
    assert registry is not None
    assert registry.count() == 0


def test_tool_registry_register(registry):
    """ToolRegistry peut enregistrer un tool."""
    tool = ToolDefinition(
        name="test_tool",
        description="Test",
        function=lambda: None
    )
    
    registry.register(tool)
    
    assert registry.count() == 1
    assert "test_tool" in registry.list_tools()


def test_tool_registry_register_duplicate(registry):
    """ToolRegistry rejette tool en doublon."""
    tool = ToolDefinition(
        name="test",
        description="Test",
        function=lambda: None
    )
    
    registry.register(tool)
    
    # Dupliquer
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_tool_registry_get(registry):
    """ToolRegistry peut récupérer un tool."""
    tool = ToolDefinition(
        name="my_tool",
        description="Test",
        function=lambda: None
    )
    
    registry.register(tool)
    
    retrieved = registry.get("my_tool")
    assert retrieved is not None
    assert retrieved.name == "my_tool"


def test_tool_registry_get_not_found(registry):
    """ToolRegistry retourne None si tool pas trouvé."""
    result = registry.get("nonexistent")
    assert result is None


def test_tool_registry_unregister(registry):
    """ToolRegistry peut désenregistrer un tool."""
    tool = ToolDefinition(
        name="temp",
        description="Test",
        function=lambda: None
    )
    
    registry.register(tool)
    assert registry.count() == 1
    
    registry.unregister("temp")
    assert registry.count() == 0


def test_tool_registry_unregister_not_found(registry):
    """ToolRegistry lève erreur si tool à retirer pas trouvé."""
    with pytest.raises(ValueError, match="not found"):
        registry.unregister("nonexistent")


def test_tool_registry_list_tools(registry):
    """ToolRegistry liste tous les tools."""
    tool1 = ToolDefinition(name="tool1", description="1", function=lambda: None)
    tool2 = ToolDefinition(name="tool2", description="2", function=lambda: None)
    
    registry.register(tool1)
    registry.register(tool2)
    
    tools = registry.list_tools()
    
    assert len(tools) == 2
    assert "tool1" in tools
    assert "tool2" in tools


def test_tool_registry_emits_events(registry, event_bus):
    """ToolRegistry émet des events."""
    events = []
    event_bus.on("tool_registered", lambda e: events.append(e))
    
    tool = ToolDefinition(name="test", description="Test", function=lambda: None)
    registry.register(tool)
    
    assert len(events) == 1
    assert events[0]["tool_name"] == "test"

# --- Decorator Tests ---

def test_tool_decorator_creates_definition():
    """@tool crée une ToolDefinition."""
    @tool(
        name="add",
        description="Add two numbers",
        parameters={
            "a": {"type": "number"},
            "b": {"type": "number"}
        }
    )
    def add(a: float, b: float) -> float:
        return a + b
    
    assert hasattr(add, "tool_definition")
    assert add.tool_definition.name == "add"
    assert add.tool_definition.description == "Add two numbers"


def test_tool_decorator_preserves_function():
    """@tool preserve la fonction originale."""
    @tool(name="test", description="Test")
    def my_func(x: int) -> int:
        return x * 2
    
    # Fonction toujours callable
    result = my_func(5)
    assert result == 10


def test_tool_decorator_parameters_optional():
    """@tool fonctionne sans parameters."""
    @tool(name="simple", description="Simple tool")
    def simple_func():
        return "ok"
    
    assert simple_func.tool_definition.parameters == {}


def test_is_tool_true():
    """is_tool() détecte un tool."""
    @tool(name="test", description="Test")
    def my_tool():
        pass
    
    assert is_tool(my_tool) is True


def test_is_tool_false():
    """is_tool() retourne False pour fonction normale."""
    def normal_func():
        pass
    
    assert is_tool(normal_func) is False


def test_get_tool_definition_returns_definition():
    """get_tool_definition() retourne la définition."""
    @tool(name="my_tool", description="Test")
    def my_func():
        pass
    
    tool_def = get_tool_definition(my_func)
    
    assert tool_def is not None
    assert tool_def.name == "my_tool"


def test_get_tool_definition_returns_none():
    """get_tool_definition() retourne None pour fonction normale."""
    def normal_func():
        pass
    
    tool_def = get_tool_definition(normal_func)
    assert tool_def is None

# --- ToolExecutor Tests ---

@pytest.fixture
def executor(config, event_bus, registry):
    exe = ToolExecutor(config, event_bus, registry)
    exe.start()
    yield exe
    exe.stop()


def test_tool_executor_creation(config, event_bus, registry):
    """ToolExecutor peut être créé."""
    executor = ToolExecutor(config, event_bus, registry)
    assert executor is not None


def test_tool_executor_execute_success(executor, registry):
    """ToolExecutor peut exécuter un tool."""
    # Tool simple
    @tool(
        name="add",
        description="Add numbers",
        parameters={
            "a": {"type": "number"},
            "b": {"type": "number"}
        }
    )
    def add(a: float, b: float) -> float:
        return a + b
    
    registry.register(add.tool_definition)
    
    # Exécuter
    result = executor.execute("add", {"a": 2, "b": 3})
    
    assert result["success"] is True
    assert result["result"] == 5


def test_tool_executor_execute_not_found(executor):
    """ToolExecutor gère tool non trouvé."""
    result = executor.execute("nonexistent", {})
    
    assert result["success"] is False
    assert "not found" in result["error"]


def test_tool_executor_execute_invalid_args(executor, registry):
    """ToolExecutor valide les arguments."""
    @tool(
        name="test",
        description="Test",
        parameters={"x": {"type": "integer"}}
    )
    def test_func(x: int) -> int:
        return x
    
    registry.register(test_func.tool_definition)
    
    # Mauvais type
    result = executor.execute("test", {"x": "not_a_number"})
    
    assert result["success"] is False
    assert "Invalid arguments" in result["error"]


def test_tool_executor_execute_missing_arg(executor, registry):
    """ToolExecutor détecte argument manquant."""
    @tool(
        name="test",
        description="Test",
        parameters={"required": {"type": "string", "required": True}}
    )
    def test_func(required: str) -> str:
        return required
    
    registry.register(test_func.tool_definition)
    
    # Argument manquant
    result = executor.execute("test", {})
    
    assert result["success"] is False
    assert "Missing required parameter" in result["error"]


def test_tool_executor_execute_function_error(executor, registry):
    """ToolExecutor gère erreur dans fonction."""
    @tool(name="crash", description="Crash")
    def crash_func():
        raise ValueError("Intentional crash")
    
    registry.register(crash_func.tool_definition)
    
    result = executor.execute("crash", {})
    
    assert result["success"] is False
    assert "Execution error" in result["error"]


def test_tool_executor_emits_events(executor, registry, event_bus):
    """ToolExecutor émet des events."""
    events = []
    event_bus.on("tool_called", lambda e: events.append(("called", e)))
    event_bus.on("tool_result", lambda e: events.append(("result", e)))
    
    @tool(name="test", description="Test")
    def test_func():
        return "ok"
    
    registry.register(test_func.tool_definition)
    
    executor.execute("test", {})
    
    assert len(events) == 2
    assert events[0][0] == "called"
    assert events[1][0] == "result"