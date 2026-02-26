"""
EVA UI — Contrat Command Registry (R-033).

Partagé par CLI, Terminal UI (R-030), API REST (R-031).
"""

from eva.ui.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
    DuplicateCommandError,
    UnknownCommandError,
)
from eva.ui.commands import make_default_registry

__all__ = [
    "Command",
    "CommandContext",
    "CommandRegistry",
    "CommandResult",
    "DuplicateCommandError",
    "UnknownCommandError",
    "make_default_registry",
]
