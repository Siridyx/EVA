"""
EVAEngine — Moteur central de l'assistant EVA

Responsabilités :
- Orchestrer le pipeline de traitement EVA
- Gérer le cycle de vie de l'application
- Coordonner les composants (LLM, memory, agents) en P1
- Émettre des événements pour observabilité

Architecture :
- Hérite de EvaComponent (config + event_bus + lifecycle)
- Pipeline configurable (sequential par défaut)
- Mode minimal P0 : structure prête pour P1
- Pas de logique métier complexe avant R-011+

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Tous les événements documentés
"""

from typing import Optional, Dict, Any

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class EVAEngine(EvaComponent):
    """
    Moteur central de l'assistant EVA.
    
    Orchestre le pipeline de traitement et coordonne les composants.
    En Phase 0, fournit la structure de base. La logique métier
    (LLM, conversation, agents) sera ajoutée en Phase 1.
    
    Architecture :
        - Hérite de EvaComponent (lifecycle standard)
        - Pipeline configurable via config.yaml
        - Mode sequential par défaut
        - Extensible pour P1 (plugins, agents, etc.)
    
    Usage:
        config = ConfigManager()
        bus = EventBus()
        engine = EVAEngine(config, bus)
        
        engine.start()
        # ... utilisation ...
        engine.stop()
    
    Events émis :
        - engine_initializing : Avant initialisation pipeline
        - engine_ready : Pipeline prêt
        - engine_starting : Démarrage en cours
        - engine_running : Moteur opérationnel
        - engine_stopping : Arrêt en cours
        - engine_stopped : Moteur arrêté
        - engine_error : Erreur dans le pipeline
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None
    ) -> None:
        """
        Initialise le moteur EVA.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du moteur (défaut: "EVAEngine")
        
        Example:
            >>> config = ConfigManager()
            >>> bus = EventBus()
            >>> engine = EVAEngine(config, bus)
        """
        super().__init__(config, event_bus, name or "EVAEngine")
        
        # Configuration pipeline
        self._pipeline_mode: str = self.get_config("engine.pipeline_mode", "sequential")
        self._auto_start: bool = self.get_config("engine.auto_start", False)
        
        # État pipeline (P0 minimal)
        self._pipeline_initialized: bool = False
        
        # Components (P1 : LLM, Memory, Agents, etc.)
        # Pour l'instant : None (structure prête)
        self._llm_client = None
        self._memory_manager = None
        self._conversation_engine = None
        
        self.emit("engine_initializing", {
            "engine": self.name,
            "pipeline_mode": self._pipeline_mode,
            "auto_start": self._auto_start
        })
        
        # Auto-start si configuré
        if self._auto_start:
            self.start()
    
    # --- Lifecycle (override EvaComponent) ---
    
    def _do_start(self) -> None:
        """
        Démarre le moteur EVA.
        
        Phase 0 :
            - Initialise le pipeline (structure vide)
            - Émet engine_ready
        
        Phase 1 (futur) :
            - Démarrera LLM, Memory, Conversation
            - Chargera les plugins
        """
        self.emit("engine_starting", {"engine": self.name})
        
        # Initialiser le pipeline
        self._initialize_pipeline()
        
        self.emit("engine_ready", {
            "engine": self.name,
            "pipeline_mode": self._pipeline_mode
        })
        
        self.emit("engine_running", {"engine": self.name})
    
    def _do_stop(self) -> None:
        """
        Arrête le moteur EVA proprement.
        
        Phase 0 :
            - Cleanup pipeline
        
        Phase 1 (futur) :
            - Arrêtera les composants (LLM, Memory, etc.)
            - Sauvegarde état
        """
        self.emit("engine_stopping", {"engine": self.name})
        
        # Cleanup pipeline
        self._cleanup_pipeline()
        
        self.emit("engine_stopped", {"engine": self.name})

# --- Configuration ---
    
    def set_conversation_engine(self, conversation_engine: Any) -> None:
        """
        Configure le ConversationEngine (P1+).
        
        Args:
            conversation_engine: Instance de ConversationEngine
        
        Note:
            Doit être appelé après __init__() et avant start().
        
        Example:
            >>> engine = EVAEngine(config, bus)
            >>> conv = ConversationEngine(config, bus, memory, prompt, llm)
            >>> engine.set_conversation_engine(conv)
            >>> engine.start()
        """
        self._conversation_engine = conversation_engine
        self.emit("conversation_engine_configured", {})
    
    # --- Pipeline (P0 minimal) ---
    
    def _initialize_pipeline(self) -> None:
        """
        Initialise le pipeline de traitement.
        
        Phase 0 : Structure vide prête pour P1
        Phase 1 : Initialisera LLM, Memory, Conversation
        
        Raises:
            RuntimeError: Si pipeline déjà initialisé
        """
        if self._pipeline_initialized:
            return  # Idempotence
        
        # P0 : Aucun composant à initialiser
        # P1 : self._llm_client = LLMClient(...)
        #      self._memory_manager = MemoryManager(...)
        #      self._conversation_engine = ConversationEngine(...)
        
        self._pipeline_initialized = True
    
    def _cleanup_pipeline(self) -> None:
        """
        Nettoie le pipeline.
        
        Phase 0 : Reset flags
        Phase 1 : Arrêtera les composants
        """
        # P0 : Simple reset
        self._pipeline_initialized = False
        
        # P1 : Stop des composants
        # if self._llm_client:
        #     self._llm_client.stop()
        # if self._memory_manager:
        #     self._memory_manager.stop()
    
    # --- API Publique (P1) ---
    
    def process(self, user_input: str) -> str:
        """
        Traite un message utilisateur.
        
        Pipeline P1 :
            user_input → ConversationEngine.respond() → assistant_reply
        
        Args:
            user_input: Message utilisateur
        
        Returns:
            Réponse générée
        
        Raises:
            RuntimeError: Si moteur pas démarré
        
        Example:
            >>> engine.start()
            >>> reply = engine.process("Bonjour EVA")
            >>> print(reply)
            "Bonjour ! Comment puis-je vous aider ?"
        """
        if not self.is_running:
            raise RuntimeError("EVAEngine not running. Call start() first.")
        
        self.emit("message_received", {
            "input_length": len(user_input)
        })
        
        # P1 : ConversationEngine integration
        
        # Vérifier si ConversationEngine disponible
        if not hasattr(self, '_conversation_engine') or self._conversation_engine is None:
            # Fallback si pas configuré (ne devrait pas arriver en P1+)
            return (
                "ConversationEngine not configured. "
                "EVA needs proper initialization with Memory, Prompt, and LLM components."
            )
        
        # Appeler ConversationEngine
        try:
            reply = self._conversation_engine.respond(user_input)
            return reply
        except Exception as e:
            # Erreur conversation (LLM unavailable, etc)
            self.emit("engine_error", {
                "stage": "conversation",
                "error": str(e)
            })
            
            # Fallback user-friendly
            return (
                "Désolé, je rencontre un problème technique. "
                "Veuillez réessayer dans quelques instants."
            )
    
    # --- Introspection ---
    
    @property
    def pipeline_mode(self) -> str:
        """Mode du pipeline (sequential/parallel)."""
        return self._pipeline_mode
    
    @property
    def pipeline_initialized(self) -> bool:
        """Le pipeline est-il initialisé ?"""
        return self._pipeline_initialized
    
    def status(self) -> dict:
        """
        Retourne l'état complet du moteur.
        
        Returns:
            Dict avec état détaillé
        
        Example:
            >>> engine.status()
            {
                'name': 'EVAEngine',
                'running': True,
                'pipeline_mode': 'sequential',
                'pipeline_initialized': True,
                'components': {'llm': None, 'memory': None}
            }
        """
        return {
            "name": self.name,
            "running": self.is_running,
            "started": self.is_started,
            "pipeline_mode": self._pipeline_mode,
            "pipeline_initialized": self._pipeline_initialized,
            "components": {
                "llm": self._llm_client is not None,
                "memory": self._memory_manager is not None,
                "conversation": self._conversation_engine is not None,
            }
        }
    
    def __repr__(self) -> str:
        """Représentation string de EVAEngine."""
        state = "running" if self.is_running else "stopped"
        return (
            f"EVAEngine(name={self.name}, state={state}, "
            f"mode={self._pipeline_mode})"
        )