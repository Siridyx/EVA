"""Tests pour demo tools"""

import pytest
from eva.tools.demo_tools import get_time, calc, list_plugins, get_status, register_demo_tools
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.tools.tool_registry import ToolRegistry


def test_get_time_tool():
    """get_time() retourne l'heure."""
    result = get_time("Tokyo")
    
    assert result["city"] == "Tokyo"
    assert "time" in result
    assert "timezone" in result


def test_calc_tool_addition():
    """calc() calcule addition."""
    result = calc("2 + 3")
    
    assert result["expression"] == "2 + 3"
    assert result["result"] == 5.0


def test_calc_tool_multiplication():
    """calc() calcule multiplication."""
    result = calc("10 * 5")
    
    assert result["result"] == 50.0


def test_calc_tool_invalid_chars():
    """calc() rejette caractères invalides."""
    result = calc("import os")
    
    assert "error" in result
    assert "Invalid characters" in result["error"]


def test_list_plugins_tool():
    """list_plugins() retourne liste."""
    result = list_plugins()
    
    assert "count" in result
    assert "plugins" in result
    assert isinstance(result["plugins"], list)


def test_get_status_tool():
    """get_status() retourne status."""
    result = get_status()
    
    assert result["status"] == "running"
    assert "version" in result


def test_register_demo_tools():
    """register_demo_tools() enregistre tous les tools."""
    config = ConfigManager()
    bus = EventBus()
    registry = ToolRegistry(config, bus)
    registry.start()
    
    register_demo_tools(registry)
    
    tools = registry.list_tools()
    
    assert "get_time" in tools
    assert "calc" in tools
    assert "list_plugins" in tools
    assert "get_status" in tools
    assert len(tools) == 4
    
    registry.stop()


def test_demo_tools_have_definitions():
    """Tous les demo tools ont des ToolDefinition."""
    assert hasattr(get_time, "tool_definition")
    assert hasattr(calc, "tool_definition")
    assert hasattr(list_plugins, "tool_definition")
    assert hasattr(get_status, "tool_definition")