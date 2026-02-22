"""
PluginRegistry — Registre central pour plugins EVA

Responsabilités :
- Enregistrer/gérer plugins chargés
- Enregistrer tools (fonctions) et services (instances)
- Isolation erreurs (plugin setup failures)
- Lifecycle management

Architecture :
- Singleton-like (une instance par EVAEngine)
- Storage simple : Dict[plugin_id, plugin_instance]
- Tools : Dict[tool_name, callable]
- Services : Dict[service_name, instance]

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Isolation erreurs complète
"""

from typing import Dict, List, Optional, Any, Callable

from eva.core.eva_component import EvaComponent
from eva.plugins.plugin_base import PluginBase


class PluginContext:
    """
    Contexte passé aux plugins lors de setup().
    
    Attributes:
        registry: PluginRegistry (pour enregistrer tools/services)
        config: ConfigManager
        event_bus: EventBus
    """
    
    def __init__(self, registry, config, event_bus):
        self.registry = registry
        self.config = config
        self.event_bus = event_bus


class PluginRegistry(EvaComponent):
    """
    Registre central pour plugins EVA.
    
    Gère le cycle de vie des plugins, tools et services.
    
    Usage:
        registry = PluginRegistry(config, bus)
        registry.start()
        
        # Enregistrer plugin
        plugin = MyPlugin(config, bus)
        registry.register_plugin(plugin)
        
        # Enregistrer tool
        registry.register_tool("weather", get_weather)
        
        # Accéder
        plugins = registry.list_plugins()
        tool = registry.get_tool("weather")
    
    Note:
        - Erreurs dans plugin.setup() isolées (n'empêchent pas registry)
        - Events émis pour chaque opération
    """
    
    def __init__(self, config, event_bus, name: Optional[str] = None):
        """
        Initialise PluginRegistry.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant (défaut: "PluginRegistry")
        """
        super().__init__(config, event_bus, name or "PluginRegistry")
        
        # Storage
        self._plugins: Dict[str, PluginBase] = {}
        self._tools: Dict[str, Callable] = {}
        self._services: Dict[str, Any] = {}
    
    def _do_start(self) -> None:
        """Démarre le registre."""
        self.emit("plugin_registry_started", {})
    
    def _do_stop(self) -> None:
        """
        Arrête le registre et tous les plugins.
        
        Note: Arrête les plugins dans l'ordre inverse d'enregistrement.
        """
        # Arrêter tous les plugins
        for plugin_id in reversed(list(self._plugins.keys())):
            plugin = self._plugins[plugin_id]
            if plugin.is_running:
                try:
                    plugin.stop()
                except Exception as e:
                    self.emit("plugin_stop_error", {
                        "plugin_id": plugin_id,
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
        
        # Clear storage
        self._plugins.clear()
        self._tools.clear()
        self._services.clear()
        
        self.emit("plugin_registry_stopped", {})
    
    # --- Plugin Management ---
    
    def register_plugin(self, plugin: PluginBase) -> None:
        """
        Enregistre et configure un plugin.
        
        Args:
            plugin: Instance de PluginBase
        
        Raises:
            RuntimeError: Si registry pas démarré
            ValueError: Si plugin_id déjà enregistré
        
        Note:
            - Démarre le plugin si pas déjà started
            - Appelle plugin.setup() avec contexte
            - Erreurs dans setup() isolées (emit event, continue)
        """
        if not self.is_running:
            raise RuntimeError("PluginRegistry not started")
        
        plugin_id = plugin.plugin_id
        
        # Vérifier doublon
        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' already registered")
        
        # Event
        self.emit("plugin_registering", {
            "plugin_id": plugin_id,
            "plugin_version": plugin.plugin_version
        })
        
        try:
            # Start plugin si nécessaire
            if not plugin.is_running:
                plugin.start()
            
            # Call setup() avec contexte
            context = PluginContext(
                registry=self,
                config=self.config,
                event_bus=self.event_bus
            )
            
            plugin.setup(context)
            
            # Stocker
            self._plugins[plugin_id] = plugin
            
            # Event succès
            self.emit("plugin_registered", {
                "plugin_id": plugin_id,
                "plugin_version": plugin.plugin_version
            })
            
        except Exception as e:
            # Isolation erreur setup()
            self.emit("plugin_setup_error", {
                "plugin_id": plugin_id,
                "error": str(e),
                "exception_type": type(e).__name__
            })
            
            # Arrêter plugin si started
            if plugin.is_running:
                try:
                    plugin.stop()
                except Exception:
                    pass  # Ignore erreur stop
    
    def unregister_plugin(self, plugin_id: str) -> None:
        """
        Désenregistre un plugin.
        
        Args:
            plugin_id: ID du plugin à désenregistrer
        
        Note:
            - Arrête le plugin si running
            - Supprime du registre
        """
        if plugin_id not in self._plugins:
            return  # Déjà absent
        
        plugin = self._plugins[plugin_id]
        
        # Arrêter si running
        if plugin.is_running:
            try:
                plugin.stop()
            except Exception as e:
                self.emit("plugin_stop_error", {
                    "plugin_id": plugin_id,
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Supprimer
        del self._plugins[plugin_id]
        
        self.emit("plugin_unregistered", {
            "plugin_id": plugin_id
        })
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        Récupère un plugin par ID.
        
        Args:
            plugin_id: ID du plugin
        
        Returns:
            Plugin ou None si absent
        """
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """
        Liste les IDs de tous les plugins enregistrés.
        
        Returns:
            Liste des plugin_id
        """
        return list(self._plugins.keys())
    
    # --- Tool Management ---
    
    def register_tool(self, name: str, func: Callable) -> None:
        """
        Enregistre un tool (fonction appelable).
        
        Args:
            name: Nom du tool (unique)
            func: Fonction callable
        
        Raises:
            ValueError: Si name déjà enregistré
        
        Example:
            def my_tool(arg: str) -> str:
                return f"Result: {arg}"
            
            registry.register_tool("my_tool", my_tool)
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        
        self._tools[name] = func
        
        self.emit("tool_registered", {
            "tool_name": name
        })
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Récupère un tool par nom.
        
        Args:
            name: Nom du tool
        
        Returns:
            Callable ou None si absent
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """
        Liste tous les tools enregistrés.
        
        Returns:
            Liste des noms de tools
        """
        return list(self._tools.keys())
    
    # --- Service Management ---
    
    def register_service(self, name: str, instance: Any) -> None:
        """
        Enregistre un service (instance).
        
        Args:
            name: Nom du service (unique)
            instance: Instance du service
        
        Raises:
            ValueError: Si name déjà enregistré
        
        Example:
            class WeatherService:
                def get_weather(self, city):
                    return f"Weather in {city}"
            
            service = WeatherService()
            registry.register_service("weather", service)
        """
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")
        
        self._services[name] = instance
        
        self.emit("service_registered", {
            "service_name": name
        })
    
    def get_service(self, name: str) -> Optional[Any]:
        """
        Récupère un service par nom.
        
        Args:
            name: Nom du service
        
        Returns:
            Instance ou None si absent
        """
        return self._services.get(name)
    
    def list_services(self) -> List[str]:
        """
        Liste tous les services enregistrés.
        
        Returns:
            Liste des noms de services
        """
        return list(self._services.keys())
    
    # --- Introspection ---
    
    @property
    def plugin_count(self) -> int:
        """Nombre de plugins enregistrés."""
        return len(self._plugins)
    
    @property
    def tool_count(self) -> int:
        """Nombre de tools enregistrés."""
        return len(self._tools)
    
    @property
    def service_count(self) -> int:
        """Nombre de services enregistrés."""
        return len(self._services)
    
    def __repr__(self) -> str:
        """Représentation string du registre."""
        state = "running" if self.is_running else "stopped"
        return (
            f"PluginRegistry(state={state}, "
            f"plugins={self.plugin_count}, "
            f"tools={self.tool_count}, "
            f"services={self.service_count})"
        )