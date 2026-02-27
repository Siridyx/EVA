"""
EVA - Assistant IA Personnel

Un assistant conversationnel intelligent et extensible.

Versioning : source unique = pyproject.toml [project].version
  → importlib.metadata lit la version au runtime depuis le package installé
  → Fallback "dev" si le package n'est pas installé (pip install -e . requis)
  → Règle de bump : modifier uniquement pyproject.toml, jamais ce fichier
"""

try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError

    __version__: str = _pkg_version("eva-assistant")
except PackageNotFoundError:
    # Package non installé — lancer : pip install -e .
    # Ce fallback ne doit jamais apparaître en production.
    __version__ = "dev"

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
