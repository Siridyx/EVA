"""
EventBus — Bus d'événements central synchrone

Responsabilités :
- Permettre communication découplée entre composants EVA
- Enregistrer/désenregistrer des handlers d'événements
- Émettre des événements avec payload typé
- Isoler les erreurs (un handler qui crash ne bloque pas les autres)

Architecture (ADR-005) :
- Synchrone en Phase 0
- Interface stable pour migration async ultérieure
- Handlers typés : Callable[[Dict[str, Any]], None]

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Gestion d'erreurs robuste
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict


# Type alias pour handler
EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """
    Bus d'événements synchrone pour communication inter-composants.
    
    Permet aux composants EVA de communiquer sans couplage direct.
    Les composants peuvent émettre des événements (emit) et
    s'abonner à des événements (on).
    
    Architecture :
        - Synchrone : handlers exécutés dans l'ordre d'enregistrement
        - Isolation : un handler qui crash n'affecte pas les autres
        - Typage : payload toujours Dict[str, Any]
    
    Usage:
        bus = EventBus()
        
        # Enregistrer un handler
        def on_user_message(payload):
            print(f"Message: {payload['text']}")
        
        bus.on("user_message", on_user_message)
        
        # Émettre un événement
        bus.emit("user_message", {"text": "Bonjour EVA"})
    
    Note:
        Cette implémentation est synchrone (Phase 0).
        Migration async possible en P1 sans changer l'interface.
    """
    
    def __init__(self) -> None:
        """Initialise le bus d'événements."""
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._logger: logging.Logger = logging.getLogger(__name__)
    
    # --- Enregistrement ---
    
    def on(self, event: str, handler: EventHandler) -> None:
        """
        Enregistre un handler pour un événement.
        
        Args:
            event: Nom de l'événement (ex: "user_message", "llm_response")
            handler: Fonction appelée lors de l'émission
                    Signature: (payload: Dict[str, Any]) -> None
        
        Example:
            >>> def log_event(payload):
            ...     print(payload)
            >>> bus.on("test_event", log_event)
        
        Note:
            Un même handler peut être enregistré plusieurs fois.
            Il sera appelé autant de fois qu'il est enregistré.
        """
        if not callable(handler):
            raise TypeError(
                f"Handler must be callable, got {type(handler).__name__}"
            )
        
        self._handlers[event].append(handler)
        self._logger.debug(f"Handler registered for event '{event}'")
    
    def off(self, event: str, handler: Optional[EventHandler] = None) -> None:
        """
        Désenregistre un ou tous les handlers d'un événement.
        
        Args:
            event: Nom de l'événement
            handler: Handler spécifique à retirer (optionnel)
                    Si None, retire TOUS les handlers de cet événement
        
        Example:
            >>> bus.off("test_event", specific_handler)  # Retire un handler
            >>> bus.off("test_event")  # Retire tous les handlers
        """
        if event not in self._handlers:
            return
        
        if handler is None:
            # Retirer tous les handlers
            del self._handlers[event]
            self._logger.debug(f"All handlers removed for event '{event}'")
        else:
            # Retirer un handler spécifique
            handlers = self._handlers[event]
            
            # Retirer toutes les occurrences
            while handler in handlers:
                handlers.remove(handler)
            
            # Nettoyer si liste vide
            if not handlers:
                del self._handlers[event]
            
            self._logger.debug(f"Handler removed for event '{event}'")
    
    # --- Émission ---
    
    def emit(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Émet un événement vers tous les handlers enregistrés.
        
        Args:
            event: Nom de l'événement
            payload: Données à transmettre (optionnel, {} par défaut)
        
        Behavior:
            - Handlers exécutés dans l'ordre d'enregistrement
            - Si un handler crash, les autres continuent
            - Exceptions loggées mais pas propagées
        
        Example:
            >>> bus.emit("user_message", {"text": "Hello", "user_id": 123})
        
        Note:
            En synchrone, emit() bloque jusqu'à ce que tous les
            handlers aient terminé.
        """
        if payload is None:
            payload = {}
        
        if not isinstance(payload, dict):
            raise TypeError(
                f"Payload must be dict, got {type(payload).__name__}"
            )
        
        handlers = self._handlers.get(event, [])
        
        if not handlers:
            self._logger.debug(f"No handlers for event '{event}'")
            return
        
        self._logger.debug(
            f"Emitting event '{event}' to {len(handlers)} handler(s)"
        )
        
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                # Isoler les erreurs : un handler qui crash ne bloque pas
                self._logger.error(
                    f"Handler {handler.__name__} failed for event '{event}': {e}",
                    exc_info=True
                )
    
    # --- Introspection ---
    
    def events(self) -> List[str]:
        """
        Liste tous les événements ayant au moins un handler.
        
        Returns:
            Liste des noms d'événements
        
        Example:
            >>> bus.on("event_a", lambda p: None)
            >>> bus.on("event_b", lambda p: None)
            >>> bus.events()
            ['event_a', 'event_b']
        """
        return list(self._handlers.keys())
    
    def handler_count(self, event: str) -> int:
        """
        Nombre de handlers enregistrés pour un événement.
        
        Args:
            event: Nom de l'événement
        
        Returns:
            Nombre de handlers (0 si aucun)
        
        Example:
            >>> bus.on("test", lambda p: None)
            >>> bus.handler_count("test")
            1
        """
        return len(self._handlers.get(event, []))
    
    def clear(self) -> None:
        """
        Supprime tous les handlers de tous les événements.
        
        Utilisé principalement pour les tests.
        
        Example:
            >>> bus.clear()
            >>> bus.events()
            []
        """
        self._handlers.clear()
        self._logger.debug("All handlers cleared")
    
    # --- Représentation ---
    
    def __repr__(self) -> str:
        """Représentation string de l'EventBus."""
        event_count = len(self._handlers)
        total_handlers = sum(len(h) for h in self._handlers.values())
        return (
            f"EventBus(events={event_count}, "
            f"total_handlers={total_handlers})"
        )