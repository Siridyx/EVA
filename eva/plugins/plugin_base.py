"""
PluginBase — Classe abstraite pour plugins EVA

Responsabilités :
- Définir le contrat minimal d'un plugin
- Fournir accès au contexte EVA (registry, config, event_bus)
- Isolation erreurs (un plugin crash ne bloque pas EVA)

Architecture :
- Hérite de EvaComponent (lifecycle standard)
- setup() appelé au chargement
- Accès registry via context

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Pas d'écriture dans plugins/
- Events uniquement (pas de logs user-facing)
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from eva.core.eva_component import EvaComponent


class PluginBase(EvaComponent, ABC):
    """
    Classe de base abstraite pour tous les plugins EVA.
    
    Tous les plugins doivent hériter de cette classe et implémenter setup().
    
    Attributes:
        plugin_id: Identifiant unique du plugin (ex: "weather_plugin")
        plugin_version: Version sémantique (ex: "1.0.0")
    
    Usage:
        class MyPlugin(PluginBase):
            plugin_id = "my_plugin"
            plugin_version = "1.0.0"
            
            def setup(self, context):
                # Enregistrer tools/services
                context.registry.register_tool("my_tool", self.my_function)
            
            def my_function(self, arg):
                return f"Result: {arg}"
    
    Note:
        - setup() est appelé après start()
        - Erreurs dans setup() sont isolées (n'empêchent pas EVA de démarrer)
        - Pas d'écriture dans plugins/ (utiliser data/ si besoin)
    """
    
    # Attributs de classe obligatoires (à override)
    plugin_id: str = ""
    plugin_version: str = "0.0.0"
    
    def __init__(
        self,
        config,
        event_bus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise PluginBase.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant (défaut: plugin_id)
        """
        # Validation attributs de classe
        if not self.plugin_id:
            raise ValueError(
                f"{self.__class__.__name__} must define 'plugin_id' class attribute"
            )
        
        super().__init__(
            config,
            event_bus,
            name or f"Plugin:{self.plugin_id}"
        )
    
    def _do_start(self) -> None:
        """
        Démarre le plugin.
        
        Note: setup() sera appelé par PluginRegistry après start().
        """
        self.emit("plugin_starting", {
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version
        })
    
    def _do_stop(self) -> None:
        """Arrête le plugin."""
        self.emit("plugin_stopping", {
            "plugin_id": self.plugin_id
        })
    
    @abstractmethod
    def setup(self, context: Any) -> None:
        """
        Configure le plugin (hook principal).
        
        Appelé par PluginRegistry après start().
        Utilisé pour enregistrer tools, services, handlers.
        
        Args:
            context: Contexte plugin contenant :
                - registry: PluginRegistry (register_tool, register_service)
                - config: ConfigManager
                - event_bus: EventBus
        
        Example:
            def setup(self, context):
                # Enregistrer un tool
                context.registry.register_tool("my_tool", self.my_function)
                
                # S'abonner à des events
                context.event_bus.on("user_message", self.on_message)
        
        Note:
            - Erreurs dans setup() sont catchées par PluginRegistry
            - Ne pas faire d'écriture dans plugins/
            - Utiliser self.emit() pour events
        """
        pass
    
    def __repr__(self) -> str:
        """Représentation string du plugin."""
        state = "running" if self.is_running else "stopped"
        return (
            f"Plugin(id={self.plugin_id}, "
            f"version={self.plugin_version}, "
            f"state={state})"
        )