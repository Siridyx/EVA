"""
ToolRegistry — Catalogue central des tools

Gère l'enregistrement, la découverte et l'accès aux tools.

Responsabilités :
- Enregistrement tools
- Liste tools disponibles
- Récupération tool par name
- Validation unicité names

Standards :
- Python 3.9 strict
- Thread-safe (dict simple, pas de mutations complexes)
- Events pour observabilité
"""

from typing import Dict, List, Optional
from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.tools.tool_definition import ToolDefinition


class ToolRegistry(EvaComponent):
    """
    Registry central pour tools EVA.
    
    Permet d'enregistrer, lister et récupérer des tools.
    
    Usage:
        registry = ToolRegistry(config, bus)
        registry.start()
        
        # Enregistrer
        registry.register(tool_def)
        
        # Lister
        tools = registry.list_tools()
        
        # Récupérer
        tool = registry.get("get_weather")
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise ToolRegistry.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant
        """
        super().__init__(config, event_bus, name or "ToolRegistry")
        
        # Catalogue tools
        self._tools: Dict[str, ToolDefinition] = {}
    
    def _do_start(self) -> None:
        """Démarre le registry."""
        self.emit("tool_registry_started", {
            "registry": self.name
        })
    
    def _do_stop(self) -> None:
        """Arrête le registry."""
        self.emit("tool_registry_stopped", {
            "registry": self.name,
            "tools_count": len(self._tools)
        })
    
    # --- API publique ---
    
    def register(self, tool: ToolDefinition) -> None:
        """
        Enregistre un tool.
        
        Args:
            tool: ToolDefinition à enregistrer
        
        Raises:
            ValueError: Si tool avec même name existe déjà
            RuntimeError: Si registry pas démarré
        
        Example:
            >>> tool = ToolDefinition(name="test", ...)
            >>> registry.register(tool)
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        # Vérifier unicité
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' already registered"
            )
        
        # Enregistrer
        self._tools[tool.name] = tool
        
        # Event
        self.emit("tool_registered", {
            "tool_name": tool.name,
            "parameters": list(tool.parameters.keys()),
            "description": tool.description
        })
    
    def unregister(self, tool_name: str) -> None:
        """
        Désenregistre un tool.
        
        Args:
            tool_name: Nom du tool à retirer
        
        Raises:
            ValueError: Si tool n'existe pas
            RuntimeError: Si registry pas démarré
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        if tool_name not in self._tools:
            raise ValueError(
                f"Tool '{tool_name}' not found"
            )
        
        # Retirer
        del self._tools[tool_name]
        
        # Event
        self.emit("tool_unregistered", {
            "tool_name": tool_name
        })
    
    def get(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Récupère un tool par name.
        
        Args:
            tool_name: Nom du tool
        
        Returns:
            ToolDefinition si trouvé, None sinon
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        Liste tous les tools disponibles.
        
        Returns:
            Liste des noms de tools
        
        Example:
            >>> registry.list_tools()
            ['get_weather', 'calc', 'get_time']
        """
        return list(self._tools.keys())
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """
        Récupère toutes les définitions.
        
        Returns:
            Liste de ToolDefinition
        """
        return list(self._tools.values())
    
    def count(self) -> int:
        """
        Compte le nombre de tools enregistrés.
        
        Returns:
            Nombre de tools
        """
        return len(self._tools)
    
    def clear(self) -> None:
        """
        Vide le registry (utile pour tests).
        
        Raises:
            RuntimeError: Si registry pas démarré
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        count = len(self._tools)
        self._tools.clear()
        
        self.emit("tool_registry_cleared", {
            "tools_cleared": count
        })
    
    def __repr__(self) -> str:
        """Représentation string."""
        state = "running" if self.is_running else "stopped"
        return f"ToolRegistry(state={state}, tools={len(self._tools)})"