"""
EVA Tools — Système de tools/fonctions appelables

Permet à EVA d'appeler des fonctions Python depuis une conversation.

Architecture :
- ToolDefinition : Modèle de données
- ToolRegistry : Catalogue central
- ToolExecutor : Exécution sécurisée
- @tool decorator : Enregistrement simple

Standards :
- Python 3.9 strict
- Provider-agnostic
- Validation stricte
- Pas eval() ou import dynamique
"""

from eva.tools.tool_definition import ToolDefinition
from eva.tools.tool_registry import ToolRegistry
from eva.tools.tool_executor import ToolExecutor
from eva.tools.decorator import tool, is_tool, get_tool_definition
from eva.tools.demo_tools import register_demo_tools

__all__ = [
    "ToolDefinition",
    "ToolRegistry",
    "ToolExecutor",
    "tool",
    "is_tool",
    "get_tool_definition",
    "register_demo_tools",
]