"""
Tool Decorator — Simplification enregistrement tools

Permet de déclarer des tools avec un simple decorator.

Usage:
    @tool(
        name="get_weather",
        description="Get weather for a city",
        parameters={
            "city": {"type": "string", "description": "City name"}
        }
    )
    def get_weather(city: str) -> dict:
        return {"city": city, "temp": 22}

Standards :
- Python 3.9 strict
- Pas de magie noire
- Validation stricte
"""

from typing import Dict, Any, Callable, Optional
from functools import wraps
from eva.tools.tool_definition import ToolDefinition


def tool(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Dict[str, Any]]] = None,
    returns: Optional[str] = None
) -> Callable:
    """
    Decorator pour créer un ToolDefinition depuis une fonction.
    
    Args:
        name: Nom du tool (snake_case)
        description: Description pour le LLM
        parameters: Schéma JSON des paramètres
        returns: Description optionnelle du retour
    
    Returns:
        Decorator qui crée un ToolDefinition
    
    Example:
        >>> @tool(
        ...     name="add",
        ...     description="Add two numbers",
        ...     parameters={
        ...         "a": {"type": "number"},
        ...         "b": {"type": "number"}
        ...     }
        ... )
        ... def add(a: float, b: float) -> float:
        ...     return a + b
        
        >>> add.tool_definition
        ToolDefinition(name='add', ...)
    """
    def decorator(func: Callable) -> Callable:
        """Decorator interne."""
        
        # Créer ToolDefinition
        tool_def = ToolDefinition(
            name=name,
            description=description,
            function=func,
            parameters=parameters or {},
            returns=returns
        )
        
        # Wrapper qui preserve la fonction originale
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Attacher ToolDefinition à la fonction
        wrapper.tool_definition = tool_def
        
        return wrapper
    
    return decorator


def is_tool(func: Callable) -> bool:
    """
    Vérifie si une fonction est un tool.
    
    Args:
        func: Fonction à vérifier
    
    Returns:
        True si la fonction a été décorée avec @tool
    
    Example:
        >>> @tool(name="test", description="Test")
        ... def my_func():
        ...     pass
        
        >>> is_tool(my_func)
        True
    """
    return hasattr(func, "tool_definition")


def get_tool_definition(func: Callable) -> Optional[ToolDefinition]:
    """
    Récupère la ToolDefinition d'une fonction.
    
    Args:
        func: Fonction décorée
    
    Returns:
        ToolDefinition si existe, None sinon
    
    Example:
        >>> @tool(name="test", description="Test")
        ... def my_func():
        ...     pass
        
        >>> tool_def = get_tool_definition(my_func)
        >>> tool_def.name
        'test'
    """
    return getattr(func, "tool_definition", None)