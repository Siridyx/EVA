"""
EVA - Assistant IA Personnel

Un assistant conversationnel intelligent et extensible.
"""

__version__ = "0.2.0-p2"
__author__ = "Siridyx"
__description__ = "Assistant IA personnel intelligent et extensible"

# Exports publics
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.core.eva_component import EvaComponent
from eva.core.eva_engine import EVAEngine

__all__ = [
    "ConfigManager",
    "EventBus",
    "EvaComponent",
    "EVAEngine",
    "__version__",
]