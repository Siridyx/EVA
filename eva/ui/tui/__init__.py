"""
EVA TUI — Terminal UI Textual (R-030).

Interface graphique en terminal construite sur le contrat R-033.
Lancement : eva --tui
"""

from eva.ui.tui.app import EvaTuiApp, main

__all__ = [
    "EvaTuiApp",
    "main",
]
