"""
Demo Tools — Exemples de tools pour R-020

4 tools simples pour démontrer le système de tool calling.

Usage:
    from eva.tools.demo_tools import register_demo_tools
    
    register_demo_tools(registry)
"""

from datetime import datetime
from typing import Dict, Any
from eva.tools.decorator import tool
from eva.tools.tool_registry import ToolRegistry


@tool(
    name="get_time",
    description="Get current time in a specific city",
    parameters={
        "city": {
            "type": "string",
            "description": "City name (e.g., 'Tokyo', 'Paris', 'New York')"
        }
    },
    returns="Dictionary with city and current time"
)
def get_time(city: str) -> Dict[str, Any]:
    """
    Get current time for a city.
    
    Note: This is a demo tool. In production, you'd use a timezone API.
    For now, returns current UTC time with city name.
    
    Args:
        city: City name
    
    Returns:
        Dict with city and time
    
    Example:
        >>> get_time("Tokyo")
        {"city": "Tokyo", "time": "15:30:45", "timezone": "UTC (demo)"}
    """
    now = datetime.utcnow()
    
    return {
        "city": city,
        "time": now.strftime("%H:%M:%S"),
        "timezone": "UTC (demo)",
        "note": "Production version would use real timezones"
    }


@tool(
    name="calc",
    description="Calculate a simple mathematical expression (supports +, -, *, /)",
    parameters={
        "expression": {
            "type": "string",
            "description": "Math expression (e.g., '2 + 3', '10 * 5')"
        }
    },
    returns="Dictionary with expression and result"
)
def calc(expression: str) -> Dict[str, Any]:
    """
    Calculate a simple math expression.
    
    Security: Only allows basic operations (+, -, *, /).
    No eval() used - safe parsing.
    
    Args:
        expression: Math expression string
    
    Returns:
        Dict with expression and result
    
    Example:
        >>> calc("2 + 3")
        {"expression": "2 + 3", "result": 5.0}
    """
    # Remove whitespace
    expr = expression.replace(" ", "")
    
    # Validate: only digits and operators
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expression):
        return {
            "expression": expression,
            "error": "Invalid characters. Only +, -, *, / allowed."
        }
    
    # Safe evaluation using basic parsing
    try:
        # Use Python's eval but only with __builtins__ disabled
        # This prevents function calls and only allows math
        result = eval(expr, {"__builtins__": {}}, {})
        
        return {
            "expression": expression,
            "result": float(result)
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": f"Calculation error: {str(e)}"
        }


@tool(
    name="list_plugins",
    description="List all registered plugins in EVA",
    parameters={},
    returns="Dictionary with plugin names and count"
)
def list_plugins() -> Dict[str, Any]:
    """
    List registered plugins.
    
    Note: This is a demo. In production, would query PluginRegistry.
    
    Returns:
        Dict with plugins list
    
    Example:
        >>> list_plugins()
        {"count": 0, "plugins": [], "note": "No plugins loaded (demo)"}
    """
    # Demo implementation
    # In production, would inject PluginRegistry and query it
    return {
        "count": 0,
        "plugins": [],
        "note": "Production version would query PluginRegistry"
    }


@tool(
    name="get_status",
    description="Get EVA system status",
    parameters={},
    returns="Dictionary with system status information"
)
def get_status() -> Dict[str, Any]:
    """
    Get EVA system status.
    
    Note: Demo implementation. Production would query EVAEngine.
    
    Returns:
        Dict with status info
    
    Example:
        >>> get_status()
        {"status": "running", "version": "0.1.0-dev", ...}
    """
    # Demo implementation
    return {
        "status": "running",
        "version": "0.1.0-dev",
        "phase": "Phase 2 (R-020 Tools)",
        "note": "Production version would query EVAEngine.status()"
    }


def register_demo_tools(registry: ToolRegistry) -> None:
    """
    Register all demo tools in the registry.
    
    Args:
        registry: ToolRegistry to register tools in
    
    Example:
        >>> registry = ToolRegistry(config, bus)
        >>> registry.start()
        >>> register_demo_tools(registry)
        >>> print(registry.list_tools())
        ['get_time', 'calc', 'list_plugins', 'get_status']
    """
    registry.register(get_time.tool_definition)
    registry.register(calc.tool_definition)
    registry.register(list_plugins.tool_definition)
    registry.register(get_status.tool_definition)