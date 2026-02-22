"""Tests unitaires pour Plugin System (R-015)"""

import pytest
from eva.plugins import PluginRegistry
from eva.plugins import PluginBase
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


# --- Fixtures ---

@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    bus = EventBus()
    bus.clear()
    return bus


# --- Dummy plugins pour tests ---

class DummyPlugin(PluginBase):
    """Plugin minimal pour tests."""
    plugin_id = "dummy"
    plugin_version = "1.0.0"
    
    def setup(self, context):
        """Setup minimal."""
        self.setup_called = True


class InvalidPlugin(PluginBase):
    """Plugin sans plugin_id (invalide)."""
    # Pas de plugin_id défini
    plugin_version = "1.0.0"
    
    def setup(self, context):
        pass


# --- Step 1 : PluginBase ---

def test_plugin_base_requires_plugin_id(config, event_bus):
    """PluginBase nécessite plugin_id défini."""
    with pytest.raises(ValueError, match="must define 'plugin_id'"):
        InvalidPlugin(config, event_bus)


def test_plugin_base_init(config, event_bus):
    """PluginBase s'initialise correctement."""
    plugin = DummyPlugin(config, event_bus)
    
    assert plugin.plugin_id == "dummy"
    assert plugin.plugin_version == "1.0.0"
    assert plugin.name == "Plugin:dummy"
    assert not plugin.is_running


def test_plugin_base_lifecycle(config, event_bus):
    """PluginBase lifecycle (start/stop)."""
    plugin = DummyPlugin(config, event_bus)
    
    # Start
    plugin.start()
    assert plugin.is_running
    
    # Stop
    plugin.stop()
    assert not plugin.is_running


def test_plugin_base_emits_events(config, event_bus):
    """PluginBase émet events lifecycle."""
    events = []
    event_bus.on("plugin_starting", lambda p: events.append(("starting", p)))
    event_bus.on("plugin_stopping", lambda p: events.append(("stopping", p)))
    
    plugin = DummyPlugin(config, event_bus)
    
    # Start
    plugin.start()
    assert len(events) == 1
    assert events[0][0] == "starting"
    assert events[0][1]["plugin_id"] == "dummy"
    
    # Stop
    plugin.stop()
    assert len(events) == 2
    assert events[1][0] == "stopping"


def test_plugin_base_repr(config, event_bus):
    """__repr__ retourne représentation correcte."""
    plugin = DummyPlugin(config, event_bus)
    
    # Stopped
    repr_str = repr(plugin)
    assert "Plugin" in repr_str
    assert "dummy" in repr_str
    assert "stopped" in repr_str
    
    # Running
    plugin.start()
    repr_str = repr(plugin)
    assert "running" in repr_str
    
    plugin.stop()


def test_plugin_base_setup_not_called_automatically(config, event_bus):
    """setup() n'est pas appelé automatiquement par start()."""
    plugin = DummyPlugin(config, event_bus)
    plugin.start()
    
    # setup() pas encore appelé (sera appelé par PluginRegistry)
    assert not hasattr(plugin, "setup_called")
    
    plugin.stop()


# --- Step 2 : PluginRegistry ---

def test_plugin_registry_init(config, event_bus):
    """PluginRegistry s'initialise correctement."""
    registry = PluginRegistry(config, event_bus)
    
    assert registry.name == "PluginRegistry"
    assert not registry.is_running
    assert registry.plugin_count == 0
    assert registry.tool_count == 0
    assert registry.service_count == 0


def test_plugin_registry_lifecycle(config, event_bus):
    """PluginRegistry lifecycle (start/stop)."""
    registry = PluginRegistry(config, event_bus)
    
    # Start
    registry.start()
    assert registry.is_running
    
    # Stop
    registry.stop()
    assert not registry.is_running


def test_plugin_registry_register_plugin(config, event_bus):
    """register_plugin() enregistre un plugin."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    plugin = DummyPlugin(config, event_bus)
    registry.register_plugin(plugin)
    
    # Vérifié
    assert registry.plugin_count == 1
    assert "dummy" in registry.list_plugins()
    assert registry.get_plugin("dummy") is plugin
    assert plugin.is_running
    assert hasattr(plugin, "setup_called")  # setup() appelé
    
    registry.stop()


def test_plugin_registry_register_duplicate_plugin_raises(config, event_bus):
    """register_plugin() rejette doublons."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    plugin1 = DummyPlugin(config, event_bus)
    plugin2 = DummyPlugin(config, event_bus)
    
    registry.register_plugin(plugin1)
    
    with pytest.raises(ValueError, match="already registered"):
        registry.register_plugin(plugin2)
    
    registry.stop()


def test_plugin_registry_unregister_plugin(config, event_bus):
    """unregister_plugin() désenregistre un plugin."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    plugin = DummyPlugin(config, event_bus)
    registry.register_plugin(plugin)
    
    # Désenregistrer
    registry.unregister_plugin("dummy")
    
    assert registry.plugin_count == 0
    assert "dummy" not in registry.list_plugins()
    assert not plugin.is_running  # Arrêté
    
    registry.stop()


def test_plugin_registry_register_tool(config, event_bus):
    """register_tool() enregistre un tool."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    def my_tool(arg):
        return f"Result: {arg}"
    
    registry.register_tool("my_tool", my_tool)
    
    # Vérifié
    assert registry.tool_count == 1
    assert "my_tool" in registry.list_tools()
    assert registry.get_tool("my_tool") is my_tool
    
    # Fonctionnel
    assert registry.get_tool("my_tool")("test") == "Result: test"
    
    registry.stop()


def test_plugin_registry_register_duplicate_tool_raises(config, event_bus):
    """register_tool() rejette doublons."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    registry.register_tool("tool1", lambda: None)
    
    with pytest.raises(ValueError, match="already registered"):
        registry.register_tool("tool1", lambda: None)
    
    registry.stop()


def test_plugin_registry_register_service(config, event_bus):
    """register_service() enregistre un service."""
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    class MyService:
        def method(self):
            return "service"
    
    service = MyService()
    registry.register_service("my_service", service)
    
    # Vérifié
    assert registry.service_count == 1
    assert "my_service" in registry.list_services()
    assert registry.get_service("my_service") is service
    assert registry.get_service("my_service").method() == "service"
    
    registry.stop()


def test_plugin_registry_stop_stops_plugins(config, event_bus):
    """stop() arrête tous les plugins."""
    
    # Créer 2 plugins avec IDs différents
    class Plugin1(PluginBase):
        plugin_id = "plugin1"
        plugin_version = "1.0.0"
        def setup(self, context):
            pass
    
    class Plugin2(PluginBase):
        plugin_id = "plugin2"
        plugin_version = "1.0.0"
        def setup(self, context):
            pass
    
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    plugin1 = Plugin1(config, event_bus)
    plugin2 = Plugin2(config, event_bus)
    
    registry.register_plugin(plugin1)
    registry.register_plugin(plugin2)
    
    assert plugin1.is_running
    assert plugin2.is_running
    
    # Stop registry
    registry.stop()
    
    # Plugins arrêtés
    assert not plugin1.is_running
    assert not plugin2.is_running


def test_plugin_registry_emits_events(config, event_bus):
    """PluginRegistry émet events."""
    events = []
    event_bus.on("plugin_registering", lambda p: events.append(("registering", p)))
    event_bus.on("plugin_registered", lambda p: events.append(("registered", p)))
    
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    plugin = DummyPlugin(config, event_bus)
    registry.register_plugin(plugin)
    
    # Events émis
    assert len(events) == 2
    assert events[0][0] == "registering"
    assert events[0][1]["plugin_id"] == "dummy"
    assert events[1][0] == "registered"
    
    registry.stop()


def test_plugin_registry_repr(config, event_bus):
    """__repr__ retourne représentation correcte."""
    registry = PluginRegistry(config, event_bus)
    
    repr_str = repr(registry)
    assert "PluginRegistry" in repr_str
    assert "stopped" in repr_str
    assert "plugins=0" in repr_str
    
    registry.start()
    repr_str = repr(registry)
    assert "running" in repr_str
    
    registry.stop()


    