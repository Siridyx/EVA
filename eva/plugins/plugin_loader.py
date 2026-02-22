"""
PluginLoader — Découverte et chargement de plugins

Responsabilités :
- Scanner dossier plugins/
- Découvrir modules Python valides
- Import safe mode (isolation erreurs)
- Enregistrement automatique dans PluginRegistry

Architecture :
- Découverte : *_plugin.py ou dossiers avec plugin.py
- Import : importlib.util (pas de modification sys.path)
- Isolation : try/except complet avec events
- Observabilité : events pour chaque étape

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Pas d'écriture fichiers
- Events uniquement (pas de logs user-facing)
"""

import importlib.util
from pathlib import Path
from typing import List, Dict, Optional

from eva.core.eva_component import EvaComponent
from eva.plugins.plugin_registry import PluginRegistry
from eva.plugins.plugin_base import PluginBase


class PluginLoader(EvaComponent):
    """
    Chargeur de plugins depuis dossier.
    
    Découvre et charge automatiquement les plugins Python
    depuis un dossier (défaut: plugins/).
    
    Usage:
        loader = PluginLoader(config, bus, registry)
        loader.start()
        
        # Charger plugins
        loaded, failed = loader.load_plugins()
        
        print(f"Loaded: {loaded}")
        print(f"Failed: {failed}")
    
    Convention plugin:
        Chaque plugin doit exposer:
        
        def get_plugin(config, event_bus) -> PluginBase:
            return MyPlugin(config, event_bus)
    
    Découverte (2 patterns supportés):
        1. Fichiers *_plugin.py (ex: weather_plugin.py)
        2. Dossiers avec plugin.py (ex: weather/plugin.py)
    
    Isolation:
        - Import errors isolés (n'empêchent pas autres plugins)
        - Events émis pour succès et échecs
        - Pas de modification sys.path
    """
    
    def __init__(
        self,
        config,
        event_bus,
        registry: PluginRegistry,
        plugins_dir: Optional[Path] = None,
        name: Optional[str] = None
    ):
        """
        Initialise PluginLoader.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            registry: PluginRegistry pour enregistrer plugins
            plugins_dir: Dossier plugins (défaut: projet_root/plugins/)
            name: Nom du composant (défaut: "PluginLoader")
        """
        super().__init__(config, event_bus, name or "PluginLoader")
        
        self._registry = registry
        
        # Dossier plugins (défaut: racine/plugins/)
        if plugins_dir is None:
            # Remonter depuis eva/plugins/ vers racine
            eva_root = Path(__file__).parent.parent.parent
            plugins_dir = eva_root / "plugins"
        
        self._plugins_dir = Path(plugins_dir)
    
    def _do_start(self) -> None:
        """Démarre le loader."""
        # Créer dossier plugins si absent
        if not self._plugins_dir.exists():
            self._plugins_dir.mkdir(parents=True, exist_ok=True)
            
            # Créer .gitkeep
            gitkeep = self._plugins_dir / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
        
        self.emit("plugin_loader_started", {
            "plugins_dir": str(self._plugins_dir)
        })
    
    def _do_stop(self) -> None:
        """Arrête le loader."""
        self.emit("plugin_loader_stopped", {})
    
    # --- Plugin Discovery ---
    
    def discover_plugins(self) -> List[Path]:
        """
        Découvre les plugins disponibles.
        
        Patterns supportés:
            1. *_plugin.py (ex: weather_plugin.py)
            2. */plugin.py (ex: weather/plugin.py)
        
        Returns:
            Liste des chemins vers modules plugin
        
        Note:
            Ignore:
            - __pycache__/
            - Fichiers commençant par _
            - Fichiers non .py
        """
        discovered = []
        
        if not self._plugins_dir.exists():
            return discovered
        
        # Pattern 1: *_plugin.py à plat
        for file in self._plugins_dir.glob("*_plugin.py"):
            if not file.name.startswith("_"):
                discovered.append(file)
        
        # Pattern 2: */plugin.py dans sous-dossiers
        for subdir in self._plugins_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("_"):
                plugin_file = subdir / "plugin.py"
                if plugin_file.exists():
                    discovered.append(plugin_file)
        
        return discovered
    
    # --- Plugin Loading ---
    
    def load_plugin(self, plugin_path: Path) -> Optional[PluginBase]:
        """
        Charge un plugin depuis un fichier.
        
        Args:
            plugin_path: Chemin vers module plugin
        
        Returns:
            Instance PluginBase ou None si échec
        
        Note:
            - Appelle get_plugin(config, event_bus) du module
            - Errors isolés (emit event, return None)
        """
        plugin_ref = plugin_path.stem  # Nom du fichier sans .py
        
        self.emit("plugin_loading", {
            "plugin_ref": plugin_ref,
            "plugin_path": str(plugin_path)
        })
        
        try:
            # Import module via importlib.util (safe, pas de sys.path)
            spec = importlib.util.spec_from_file_location(
                f"eva_plugin_{plugin_ref}",
                plugin_path
            )
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec from {plugin_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Appeler get_plugin()
            if not hasattr(module, "get_plugin"):
                raise AttributeError(
                    f"Plugin '{plugin_ref}' missing get_plugin() function"
                )
            
            get_plugin = getattr(module, "get_plugin")
            plugin = get_plugin(self.config, self.event_bus)
            
            # Valider type
            if not isinstance(plugin, PluginBase):
                raise TypeError(
                    f"get_plugin() must return PluginBase, got {type(plugin)}"
                )
            
            # Event succès
            self.emit("plugin_loaded", {
                "plugin_id": plugin.plugin_id,
                "plugin_version": plugin.plugin_version,
                "plugin_ref": plugin_ref
            })
            
            return plugin
            
        except Exception as e:
            # Isolation erreur
            self.emit("plugin_failed", {
                "plugin_ref": plugin_ref,
                "plugin_path": str(plugin_path),
                "error": str(e)[:200],  # Tronqué
                "exception_type": type(e).__name__
            })
            
            return None
    
    def load_plugins(self) -> tuple[List[str], Dict[str, str]]:
        """
        Charge tous les plugins disponibles.
        
        Returns:
            Tuple (loaded, failed):
            - loaded: Liste des plugin_id chargés
            - failed: Dict {plugin_ref: error_message}
        
        Note:
            - Découvre plugins dans plugins_dir
            - Charge chacun en mode safe
            - Enregistre dans registry
            - Continue même si un plugin fail
        """
        self.emit("plugin_discovery_started", {
            "plugins_dir": str(self._plugins_dir)
        })
        
        loaded = []
        failed = {}
        
        # Découvrir plugins
        plugin_paths = self.discover_plugins()
        
        for plugin_path in plugin_paths:
            plugin_ref = plugin_path.stem
            
            self.emit("plugin_discovered", {
                "plugin_ref": plugin_ref,
                "plugin_path": str(plugin_path)
            })
            
            # Charger plugin
            plugin = self.load_plugin(plugin_path)
            
            if plugin is not None:
                # Enregistrer dans registry
                try:
                    self._registry.register_plugin(plugin)
                    loaded.append(plugin.plugin_id)
                    
                except Exception as e:
                    # Erreur enregistrement
                    failed[plugin_ref] = str(e)
                    
                    self.emit("plugin_registration_failed", {
                        "plugin_id": plugin.plugin_id,
                        "plugin_ref": plugin_ref,
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
            else:
                # Erreur chargement (déjà event émis dans load_plugin)
                failed[plugin_ref] = "Failed to load (see events)"
        
        # Event final
        self.emit("plugin_discovery_finished", {
            "plugins_dir": str(self._plugins_dir),
            "loaded_count": len(loaded),
            "failed_count": len(failed),
            "loaded": loaded,
            "failed": list(failed.keys())
        })
        
        return loaded, failed
    
    # --- Introspection ---
    
    @property
    def plugins_dir(self) -> Path:
        """Dossier plugins."""
        return self._plugins_dir
    
    def __repr__(self) -> str:
        """Représentation string du loader."""
        state = "running" if self.is_running else "stopped"
        return (
            f"PluginLoader(state={state}, "
            f"plugins_dir={self._plugins_dir})"
        )