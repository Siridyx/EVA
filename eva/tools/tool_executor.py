"""
ToolExecutor — Exécution sécurisée des tools

Responsabilités :
- Validation arguments
- Exécution safe (timeout, exceptions)
- Formatting résultats
- Events observabilité

Standards :
- Python 3.9 strict
- Pas eval() ou exec()
- Validation stricte avant exécution
- Isolation erreurs
"""

from typing import Dict, Any, Optional
from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.tools.tool_registry import ToolRegistry


class ToolExecutor(EvaComponent):
    """
    Exécuteur sécurisé de tools.
    
    Valide arguments, exécute tools, gère erreurs.
    
    Usage:
        executor = ToolExecutor(config, bus, registry)
        executor.start()
        
        result = executor.execute(
            tool_name="get_weather",
            arguments={"city": "Paris"}
        )
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        registry: ToolRegistry,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise ToolExecutor.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            registry: ToolRegistry
            name: Nom du composant
        """
        super().__init__(config, event_bus, name or "ToolExecutor")
        self._registry = registry
        
        # Timeout par défaut (secondes)
        self._default_timeout = self.get_config("tools.timeout", 30)
    
    def _do_start(self) -> None:
        """Démarre l'executor."""
        self.emit("tool_executor_started", {
            "executor": self.name,
            "default_timeout": self._default_timeout
        })
    
    def _do_stop(self) -> None:
        """Arrête l'executor."""
        self.emit("tool_executor_stopped", {
            "executor": self.name
        })
    
    # --- API publique ---
    
    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Exécute un tool.
        
        Args:
            tool_name: Nom du tool
            arguments: Arguments pour le tool
            timeout: Timeout optionnel (seconds)
        
        Returns:
            Dict avec:
                - success: bool
                - result: Any (si success)
                - error: str (si échec)
                - tool_name: str
        
        Raises:
            RuntimeError: Si executor pas démarré
        
        Example:
            >>> result = executor.execute(
            ...     tool_name="add",
            ...     arguments={"a": 2, "b": 3}
            ... )
            >>> result["success"]
            True
            >>> result["result"]
            5
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        # Event début
        self.emit("tool_called", {
            "tool_name": tool_name,
            "arguments": list(arguments.keys())
        })
        
        try:
            # 1. Récupérer tool
            tool_def = self._registry.get(tool_name)
            
            if tool_def is None:
                return self._error_result(
                    tool_name,
                    f"Tool '{tool_name}' not found"
                )
            
            # 2. Valider arguments
            try:
                tool_def.validate_arguments(arguments)
            except ValueError as e:
                return self._error_result(
                    tool_name,
                    f"Invalid arguments: {e}"
                )
            
            # 3. Exécuter (simple pour P2, timeout avancé P3)
            try:
                result = tool_def.function(**arguments)
            except Exception as e:
                return self._error_result(
                    tool_name,
                    f"Execution error: {e}"
                )
            
            # 4. Success
            response = {
                "success": True,
                "result": result,
                "tool_name": tool_name
            }
            
            # Event success
            self.emit("tool_result", {
                "tool_name": tool_name,
                "success": True
            })
            
            return response
            
        except Exception as e:
            # Erreur inattendue
            return self._error_result(
                tool_name,
                f"Unexpected error: {e}"
            )
    
    def _error_result(self, tool_name: str, error: str) -> Dict[str, Any]:
        """
        Crée un résultat d'erreur.
        
        Args:
            tool_name: Nom du tool
            error: Message d'erreur
        
        Returns:
            Dict avec success=False
        """
        # Event error
        self.emit("tool_error", {
            "tool_name": tool_name,
            "error": error
        })
        
        return {
            "success": False,
            "error": error,
            "tool_name": tool_name
        }
    
    def __repr__(self) -> str:
        """Représentation string."""
        state = "running" if self.is_running else "stopped"
        return f"ToolExecutor(state={state}, timeout={self._default_timeout}s)"