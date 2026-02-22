"""Tests unitaires pour PluginLoader (R-015 Step 3)"""

import pytest
from pathlib import Path

from eva.plugins import PluginBase, PluginRegistry, PluginLoader
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


@pytest.fixture
def registry(config, event_bus):
    reg = PluginRegistry(config, event_bus)
    reg.start()
    yield reg
    reg.stop()


@pytest.fixture
def plugins_dir(tmp_path):
    """Dossier plugins temporaire."""
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    return plugins


@pytest.fixture
def loader(config, event_bus, registry, plugins_dir):
    """PluginLoader avec tmp_path."""
    ldr = PluginLoader(config, event_bus, registry, plugins_dir=plugins_dir)
    ldr.start()
    yield ldr
    ldr.stop()


# --- Step 3 : PluginLoader ---

def test_plugin_loader_init(config, event_bus, registry, plugins_dir):
    """PluginLoader s'initialise correctement."""
    loader = PluginLoader(config, event_bus, registry, plugins_dir=plugins_dir)
    
    assert loader.name == "PluginLoader"
    assert not loader.is_running
    assert loader.plugins_dir == plugins_dir


def test_plugin_loader_start_creates_dir(config, event_bus, registry, tmp_path):
    """start() crée le dossier plugins si absent."""
    plugins_dir = tmp_path / "new_plugins"
    
    assert not plugins_dir.exists()
    
    loader = PluginLoader(config, event_bus, registry, plugins_dir=plugins_dir)
    loader.start()
    
    # Créé
    assert plugins_dir.exists()
    assert (plugins_dir / ".gitkeep").exists()
    
    loader.stop()


def test_plugin_loader_discover_empty(loader):
    """discover_plugins() avec dossier vide."""
    discovered = loader.discover_plugins()
    
    assert discovered == []


def test_plugin_loader_discover_pattern_file(loader, plugins_dir):
    """discover_plugins() trouve *_plugin.py."""
    # Créer plugin
    plugin_file = plugins_dir / "test_plugin.py"
    plugin_file.write_text("# dummy plugin")
    
    discovered = loader.discover_plugins()
    
    assert len(discovered) == 1
    assert discovered[0] == plugin_file


def test_plugin_loader_discover_pattern_folder(loader, plugins_dir):
    """discover_plugins() trouve */plugin.py."""
    # Créer plugin dans dossier
    plugin_dir = plugins_dir / "test_plugin"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "plugin.py"
    plugin_file.write_text("# dummy plugin")
    
    discovered = loader.discover_plugins()
    
    assert len(discovered) == 1
    assert discovered[0] == plugin_file


def test_plugin_loader_discover_ignores_underscore(loader, plugins_dir):
    """discover_plugins() ignore fichiers commençant par _."""
    # Créer fichiers
    (plugins_dir / "_private_plugin.py").write_text("# private")
    (plugins_dir / "test_plugin.py").write_text("# ok")
    
    discovered = loader.discover_plugins()
    
    # Seulement test_plugin.py
    assert len(discovered) == 1
    assert discovered[0].name == "test_plugin.py"


def test_plugin_loader_load_plugin_success(loader, plugins_dir, config, event_bus):
    """load_plugin() charge un plugin valide."""
    # Créer plugin valide
    plugin_code = """
from eva.plugins import PluginBase

class TestPlugin(PluginBase):
    plugin_id = "test"
    plugin_version = "1.0.0"
    
    def setup(self, context):
        pass

def get_plugin(config, event_bus):
    return TestPlugin(config, event_bus)
"""
    plugin_file = plugins_dir / "test_plugin.py"
    plugin_file.write_text(plugin_code)
    
    # Charger
    plugin = loader.load_plugin(plugin_file)
    
    assert plugin is not None
    assert plugin.plugin_id == "test"
    assert plugin.plugin_version == "1.0.0"


def test_plugin_loader_load_plugin_missing_get_plugin(loader, plugins_dir):
    """load_plugin() échoue si get_plugin() manquant."""
    # Plugin sans get_plugin()
    plugin_code = "# No get_plugin()"
    plugin_file = plugins_dir / "bad_plugin.py"
    plugin_file.write_text(plugin_code)
    
    # Charger
    plugin = loader.load_plugin(plugin_file)
    
    assert plugin is None  # Échec isolé


def test_plugin_loader_load_plugin_syntax_error(loader, plugins_dir):
    """load_plugin() isole syntax error."""
    # Plugin avec erreur syntaxe
    plugin_code = "def broken("  # Syntax error
    plugin_file = plugins_dir / "broken_plugin.py"
    plugin_file.write_text(plugin_code)
    
    # Charger
    plugin = loader.load_plugin(plugin_file)
    
    assert plugin is None  # Échec isolé


def test_plugin_loader_load_plugins_success(loader, plugins_dir, config, event_bus):
    """load_plugins() charge plugins disponibles."""
    # Créer 2 plugins valides
    plugin1_code = """
from eva.plugins import PluginBase

class Plugin1(PluginBase):
    plugin_id = "plugin1"
    plugin_version = "1.0.0"
    def setup(self, context):
        pass

def get_plugin(config, event_bus):
    return Plugin1(config, event_bus)
"""
    plugin2_code = """
from eva.plugins import PluginBase

class Plugin2(PluginBase):
    plugin_id = "plugin2"
    plugin_version = "1.0.0"
    def setup(self, context):
        pass

def get_plugin(config, event_bus):
    return Plugin2(config, event_bus)
"""
    
    (plugins_dir / "plugin1_plugin.py").write_text(plugin1_code)
    (plugins_dir / "plugin2_plugin.py").write_text(plugin2_code)
    
    # Charger
    loaded, failed = loader.load_plugins()
    
    assert len(loaded) == 2
    assert "plugin1" in loaded
    assert "plugin2" in loaded
    assert len(failed) == 0


def test_plugin_loader_load_plugins_mixed(loader, plugins_dir, config, event_bus):
    """load_plugins() avec succès et échecs."""
    # Plugin 1: OK
    plugin1_code = """
from eva.plugins import PluginBase

class Plugin1(PluginBase):
    plugin_id = "plugin1"
    plugin_version = "1.0.0"
    def setup(self, context):
        pass

def get_plugin(config, event_bus):
    return Plugin1(config, event_bus)
"""
    
    # Plugin 2: Broken
    plugin2_code = "def broken("
    
    (plugins_dir / "plugin1_plugin.py").write_text(plugin1_code)
    (plugins_dir / "plugin2_plugin.py").write_text(plugin2_code)
    
    # Charger
    loaded, failed = loader.load_plugins()
    
    # Plugin1 OK, Plugin2 fail
    assert len(loaded) == 1
    assert "plugin1" in loaded
    assert len(failed) == 1
    assert "plugin2_plugin" in failed


def test_plugin_loader_emits_events(loader, plugins_dir, config, event_bus):
    """load_plugins() émet events."""
    events = []
    event_bus.on("plugin_discovery_started", lambda p: events.append(("started", p)))
    event_bus.on("plugin_discovered", lambda p: events.append(("discovered", p)))
    event_bus.on("plugin_loaded", lambda p: events.append(("loaded", p)))
    event_bus.on("plugin_discovery_finished", lambda p: events.append(("finished", p)))
    
    # Créer plugin
    plugin_code = """
from eva.plugins import PluginBase

class TestPlugin(PluginBase):
    plugin_id = "test"
    plugin_version = "1.0.0"
    def setup(self, context):
        pass

def get_plugin(config, event_bus):
    return TestPlugin(config, event_bus)
"""
    (plugins_dir / "test_plugin.py").write_text(plugin_code)
    
    # Charger
    loader.load_plugins()
    
    # Events émis
    event_types = [e[0] for e in events]
    assert "started" in event_types
    assert "discovered" in event_types
    assert "loaded" in event_types
    assert "finished" in event_types


def test_plugin_loader_repr(loader):
    """__repr__ retourne représentation correcte."""
    repr_str = repr(loader)
    
    assert "PluginLoader" in repr_str
    assert "running" in repr_str
    assert "plugins" in repr_str


def test_plugin_loader_full_integration(config, event_bus, plugins_dir):
    """Test intégration complète (registry + loader + plugin)."""
    # Setup
    registry = PluginRegistry(config, event_bus)
    registry.start()
    
    loader = PluginLoader(config, event_bus, registry, plugins_dir=plugins_dir)
    loader.start()
    
    # Créer plugin complet
    plugin_code = """
from eva.plugins import PluginBase

class IntegrationPlugin(PluginBase):
    plugin_id = "integration"
    plugin_version = "1.0.0"
    
    def setup(self, context):
        # Enregistrer tool
        context.registry.register_tool("test_tool", self.test_tool)
        
        # Enregistrer service
        context.registry.register_service("test_service", self)
    
    def test_tool(self, arg):
        return f"Tool result: {arg}"

def get_plugin(config, event_bus):
    return IntegrationPlugin(config, event_bus)
"""
    
    (plugins_dir / "integration_plugin.py").write_text(plugin_code)
    
    # Charger
    loaded, failed = loader.load_plugins()
    
    # Vérifications
    assert len(loaded) == 1
    assert "integration" in loaded
    assert len(failed) == 0
    
    # Plugin dans registry
    plugin = registry.get_plugin("integration")
    assert plugin is not None
    assert plugin.plugin_id == "integration"
    
    # Tool enregistré
    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool("test") == "Tool result: test"
    
    # Service enregistré
    service = registry.get_service("test_service")
    assert service is not None
    assert service is plugin
    
    # Cleanup
    loader.stop()
    registry.stop()