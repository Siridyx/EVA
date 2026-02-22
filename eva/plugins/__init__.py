"""
eva.plugins — Système de plugins extensible

Permet de charger des plugins tiers sans modifier le core EVA.

Usage:
    from eva.plugins import PluginBase, PluginRegistry, PluginLoader
    
    # Setup
    registry = PluginRegistry(config, bus)
    registry.start()
    
    loader = PluginLoader(config, bus, registry)
    loader.start()
    
    # Charger plugins
    loaded, failed = loader.load_plugins()
    
    print(f"Loaded: {loaded}")
    print(f"Failed: {failed}")
"""

from eva.plugins.plugin_base import PluginBase
from eva.plugins.plugin_registry import PluginRegistry, PluginContext
from eva.plugins.plugin_loader import PluginLoader

__all__ = ["PluginBase", "PluginRegistry", "PluginContext", "PluginLoader"]