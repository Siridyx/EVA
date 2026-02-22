"""
EvaComponent — Classe de base universelle pour tous les composants EVA

Responsabilités :
- Fournir accès centralisé à ConfigManager et EventBus
- Implémenter un cycle de vie standard (start/stop/shutdown)
- Offrir méthodes utilitaires (emit, get_config, get_path)
- Garantir idempotence et gestion d'erreurs robuste

Architecture :
- Injection explicite des dépendances (testable)
- Lifecycle synchrone (cohérent avec EventBus P0)
- State tracking simple (_started, _running)
- Erreurs émises + propagées (observabilité)

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Tous les composants EVA héritent de cette classe
"""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class EvaComponent(ABC):
    """
    Classe de base abstraite pour tous les composants EVA.
    
    Fournit l'infrastructure commune à tous les composants :
    - Accès configuration via self.config
    - Accès bus d'événements via self.event_bus
    - Cycle de vie standardisé (start/stop/shutdown)
    - Méthodes utilitaires pour config et events
    
    Architecture :
        - Injection de dépendances explicite
        - Lifecycle synchrone (start/stop)
        - Idempotence garantie (appels multiples safe)
        - Erreurs émises + propagées
    
    Usage:
        class MyComponent(EvaComponent):
            def _do_start(self) -> None:
                # Initialisation spécifique
                pass
            
            def _do_stop(self) -> None:
                # Nettoyage spécifique
                pass
        
        component = MyComponent(config, event_bus, name="MyComponent")
        component.start()
        component.stop()
    
    Note:
        Cette classe est abstraite mais n'impose pas de méthodes
        abstraites. Les sous-classes peuvent surcharger _do_start,
        _do_stop, _do_shutdown selon leurs besoins.
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le composant EVA.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: nom de la classe)
        
        Example:
            >>> config = ConfigManager()
            >>> bus = EventBus()
            >>> component = MyComponent(config, bus, "MyService")
        """
        self.config: ConfigManager = config
        self.event_bus: EventBus = event_bus
        self.name: str = name or self.__class__.__name__
        
        # State tracking simple
        self._started: bool = False
        self._running: bool = False
        
        # Emit component_created event
        self.emit("component_created", {
            "component": self.name,
            "type": self.__class__.__name__
        })
    
    # --- Cycle de vie ---
    
    def start(self) -> None:
        """
        Démarre le composant.
        
        Idempotent : appeler start() plusieurs fois est safe.
        Si déjà démarré, ne fait rien (no-op).
        
        Workflow :
            1. Vérifie si déjà démarré (idempotence)
            2. Emit "component_starting"
            3. Appelle _do_start() (implémentation spécifique)
            4. Marque comme démarré
            5. Emit "component_started"
        
        Raises:
            Exception: Si _do_start() échoue (après avoir émis component_error)
        
        Example:
            >>> component.start()  # Démarre
            >>> component.start()  # No-op (déjà démarré)
        """
        # Idempotence : déjà démarré → no-op
        if self._started:
            return
        
        self.emit("component_starting", {"component": self.name})
        
        try:
            self._do_start()
            self._started = True
            self._running = True
            
            self.emit("component_started", {"component": self.name})
            
        except Exception as e:
            # Emit error event (observabilité)
            self.emit("component_error", {
                "component": self.name,
                "stage": "start",
                "error": str(e),
                "exception_type": type(e).__name__
            })
            # Propager l'erreur (tests/CI détectent le problème)
            raise
    
    def stop(self) -> None:
        """
        Arrête le composant proprement.
        
        Idempotent : appeler stop() plusieurs fois est safe.
        Si déjà arrêté, ne fait rien (no-op).
        
        Workflow :
            1. Vérifie si déjà arrêté (idempotence)
            2. Emit "component_stopping"
            3. Appelle _do_stop() (nettoyage spécifique)
            4. Marque comme arrêté
            5. Emit "component_stopped"
        
        Raises:
            Exception: Si _do_stop() échoue (après avoir émis component_error)
        
        Example:
            >>> component.stop()  # Arrête
            >>> component.stop()  # No-op (déjà arrêté)
        """
        # Idempotence : pas démarré → no-op
        if not self._started:
            return
        
        self.emit("component_stopping", {"component": self.name})
        
        try:
            self._do_stop()
            self._running = False
            self._started = False
            
            self.emit("component_stopped", {"component": self.name})
            
        except Exception as e:
            # Emit error event
            self.emit("component_error", {
                "component": self.name,
                "stage": "stop",
                "error": str(e),
                "exception_type": type(e).__name__
            })
            # Propager l'erreur
            raise
    
    def shutdown(self) -> None:
        """
        Shutdown complet du composant (stop + cleanup).
        
        Appelle stop() puis _do_shutdown() pour nettoyage final.
        Utilisé typiquement en fin de vie de l'application.
        
        Example:
            >>> component.shutdown()
        """
        # Stop d'abord (idempotent)
        self.stop()
        
        # Cleanup final
        try:
            self._do_shutdown()
            self.emit("component_shutdown", {"component": self.name})
            
        except Exception as e:
            self.emit("component_error", {
                "component": self.name,
                "stage": "shutdown",
                "error": str(e),
                "exception_type": type(e).__name__
            })
            raise
    
    # --- Méthodes à surcharger (optionnel) ---
    
    def _do_start(self) -> None:
        """
        Implémentation spécifique du démarrage.
        
        À surcharger dans les sous-classes pour initialisation
        spécifique (connexions, chargement de ressources, etc.).
        
        Note:
            Ne pas appeler directement, utiliser start().
        """
        pass
    
    def _do_stop(self) -> None:
        """
        Implémentation spécifique de l'arrêt.
        
        À surcharger dans les sous-classes pour nettoyage
        spécifique (fermeture connexions, libération ressources).
        
        Note:
            Ne pas appeler directement, utiliser stop().
        """
        pass
    
    def _do_shutdown(self) -> None:
        """
        Implémentation spécifique du shutdown final.
        
        À surcharger si nettoyage supplémentaire nécessaire
        après stop() (logs finaux, métriques, etc.).
        
        Note:
            Ne pas appeler directement, utiliser shutdown().
        """
        pass
    
    # --- Méthodes utilitaires ---
    
    def emit(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Émet un événement sur le bus.
        
        Args:
            event: Nom de l'événement
            payload: Données à transmettre (optionnel)
        
        Example:
            >>> self.emit("user_message", {"text": "Hello", "user_id": 123})
        """
        if payload is None:
            payload = {}
        
        self.event_bus.emit(event, payload)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration.
        
        Args:
            key: Clé config (notation pointée)
            default: Valeur par défaut
        
        Returns:
            Valeur de config ou default
        
        Example:
            >>> self.get_config("llm.default_model")
            "gpt-4"
        """
        return self.config.get(key, default)
    
    def get_path(self, path_key: str) -> Path:
        """
        Récupère un chemin data/ absolu.
        
        Args:
            path_key: Clé du chemin (ex: "logs", "memory")
        
        Returns:
            Path absolu
        
        Example:
            >>> self.get_path("logs")
            Path("C:/Users/Sirid/Desktop/EVA/data/logs")
        """
        return self.config.get_path(path_key)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Récupère une variable d'environnement (secret).
        
        Args:
            key: Nom de la variable
            default: Valeur par défaut
        
        Returns:
            Valeur du secret ou default
        
        Example:
            >>> self.get_secret("OPENAI_API_KEY")
            "sk-..."
        """
        return self.config.get_secret(key, default)
    
    # --- État ---
    
    @property
    def is_started(self) -> bool:
        """Le composant est-il démarré ?"""
        return self._started
    
    @property
    def is_running(self) -> bool:
        """Le composant est-il en cours d'exécution ?"""
        return self._running
    
    # --- Représentation ---
    
    def __repr__(self) -> str:
        """Représentation string du composant."""
        state = "running" if self._running else ("started" if self._started else "stopped")
        return f"{self.__class__.__name__}(name={self.name}, state={state})"