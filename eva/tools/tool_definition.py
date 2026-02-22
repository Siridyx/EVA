"""
ToolDefinition — Modèle de données pour tools

Définit la structure d'un tool appelable par EVA.

Standards :
- Python 3.9 strict (dataclass)
- JSON schema léger pour paramètres
- Validation stricte
- Immutable (frozen dataclass)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable


@dataclass(frozen=True)
class ToolDefinition:
    """
    Définition d'un tool appelable.
    
    Un tool est une fonction Python que EVA peut appeler
    durant une conversation pour obtenir des informations
    ou effectuer des actions.
    
    Attributes:
        name: Nom unique du tool (snake_case)
        description: Description pour le LLM (ce que fait le tool)
        function: Fonction Python callable
        parameters: Schéma JSON léger des paramètres
        returns: Description optionnelle du retour
    
    Example:
        >>> def get_weather(city: str) -> dict:
        ...     return {"city": city, "temp": 22}
        
        >>> tool = ToolDefinition(
        ...     name="get_weather",
        ...     description="Get weather for a city",
        ...     function=get_weather,
        ...     parameters={
        ...         "city": {
        ...             "type": "string",
        ...             "description": "City name"
        ...         }
        ...     }
        ... )
    """
    
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    returns: Optional[str] = None
    
    def __post_init__(self):
        """Validation après initialisation."""
        # Valider name
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        
        if not self.name.replace("_", "").isalnum():
            raise ValueError(
                f"Tool name '{self.name}' must be alphanumeric with underscores"
            )
        
        # Valider description
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        
        # Valider function
        if not callable(self.function):
            raise ValueError("Tool function must be callable")
        
        # Valider parameters schema
        if not isinstance(self.parameters, dict):
            raise ValueError("Tool parameters must be a dict")
        
        for param_name, param_schema in self.parameters.items():
            if not isinstance(param_schema, dict):
                raise ValueError(
                    f"Parameter '{param_name}' schema must be a dict"
                )
            
            if "type" not in param_schema:
                raise ValueError(
                    f"Parameter '{param_name}' must have a 'type' field"
                )
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Valide les arguments avant exécution.
        
        Args:
            arguments: Arguments à valider
        
        Raises:
            ValueError: Si arguments invalides
        
        Note:
            Validation basique (types), pas de validation complexe.
        """
        # Vérifier arguments requis
        for param_name, param_schema in self.parameters.items():
            required = param_schema.get("required", True)
            
            if required and param_name not in arguments:
                raise ValueError(
                    f"Missing required parameter: {param_name}"
                )
        
        # Vérifier types (basique)
        for param_name, value in arguments.items():
            if param_name not in self.parameters:
                raise ValueError(
                    f"Unknown parameter: {param_name}"
                )
            
            param_schema = self.parameters[param_name]
            expected_type = param_schema["type"]
            
            # Mapping types JSON → Python
            type_mapping = {
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "object": dict,
                "array": list
            }
            
            if expected_type in type_mapping:
                expected_python_type = type_mapping[expected_type]
                
                if not isinstance(value, expected_python_type):
                    raise ValueError(
                        f"Parameter '{param_name}' must be {expected_type}, "
                        f"got {type(value).__name__}"
                    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit en dict (pour serialization).
        
        Returns:
            Dict representation (sans function)
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns
        }
    
    def __repr__(self) -> str:
        """Représentation string."""
        return f"ToolDefinition(name={self.name}, params={list(self.parameters.keys())})"