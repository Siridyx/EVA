"""
LLMClient — Interface abstraite pour providers LLM

Responsabilités :
- Définir l'interface commune pour tous les providers
- Gestion du profil model (dev/default)
- Support timeout et retries
- Mockable pour tests (transport injectable)

Architecture :
- Interface abstraite (méthodes à implémenter)
- Config-driven (models depuis config.yaml)
- Transport injectable (mockable)
- Retry logic sur erreurs transient

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import os

from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class LLMClient(EvaComponent, ABC):
    """
    Interface abstraite pour clients LLM.
    
    Tous les providers (OpenAI, Anthropic, Ollama) doivent
    implémenter cette interface.
    
    Architecture :
        - Config-driven : models depuis config.yaml
        - Transport injectable : mockable pour tests
        - Timeout + retries : robustesse réseau
        - Profils : dev (cheap) / default (best)
    
    Usage:
        # Production
        client = OpenAIProvider(config, bus)
        
        # Tests (avec mock)
        client = OpenAIProvider(config, bus, transport=mock_transport)
        
        client.start()
        response = client.complete(messages, profile="dev")
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None  # Injectable pour tests
    ) -> None:
        """
        Initialise le LLMClient.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant
            transport: Transport HTTP injectable (pour tests)
        """
        super().__init__(config, event_bus, name)
        
        # Config LLM
        self._models: Dict[str, str] = self.get_config("llm.models", {
            "dev": "gpt-4o-mini",
            "default": "gpt-4o"
        })
        self._max_tokens: int = self.get_config("llm.max_tokens", 2000)
        self._temperature: float = self.get_config("llm.temperature", 0.7)
        self._timeout: int = self.get_config("llm.timeout", 30)
        self._max_retries: int = self.get_config("llm.max_retries", 3)
        self._retry_delay: int = self.get_config("llm.retry_delay", 1)
        
        # Transport (injectable pour tests)
        self._transport = transport
    
    # --- Interface abstraite (à implémenter par providers) ---
    
    @abstractmethod
    def _do_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """
        Implémentation provider-specific de la complétion.
        
        Args:
            messages: Historique conversation
            model: Nom du modèle
            max_tokens: Limite tokens
            temperature: Température génération
        
        Returns:
            Réponse générée
        
        Note:
            Cette méthode est appelée par complete() avec retry logic.
        """
        pass

    # --- Configuration dynamique (test mode) ---
    
    def _get_timeout(self) -> float:
        """
        Récupère le timeout pour requêtes LLM.
        
        Returns:
            Timeout en secondes
        
        Note:
            En mode test (EVA_TEST_MODE=1), timeout court (0.5s).
        """
        import os
        
        # Mode test : timeout court
        if os.environ.get("EVA_TEST_MODE") == "1":
            return 0.5
        
        # Mode normal
        return self._timeout
    
    def _get_retry_config(self) -> tuple[int, float]:
        """Get retry config based on test mode."""
        is_test = os.environ.get("EVA_TEST_MODE") == "1"
        
        if is_test:
            return (1, 0.01)
        else:
            return (self._max_retries, self._retry_delay)
    
    # --- API publique (avec retry logic) ---
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        profile: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Génère une complétion (avec retry sur erreurs transient).
        
        Args:
            messages: Historique conversation (format OpenAI)
                     [{"role": "user", "content": "..."}]
            profile: Profil model ("dev" ou "default")
            max_tokens: Override max_tokens config
            temperature: Override temperature config
        
        Returns:
            Réponse générée
        
        Raises:
            RuntimeError: Si LLMClient pas démarré
            ValueError: Si profil invalide
            Exception: Si échec après retries
        
        Example:
            >>> messages = [{"role": "user", "content": "Bonjour"}]
            >>> response = client.complete(messages, profile="dev")
        """
        if not self.is_running:
            raise RuntimeError(f"{self.name} not started")
        
        # Valider profil
        if profile not in self._models:
            raise ValueError(
                f"Invalid profile '{profile}'. "
                f"Available: {list(self._models.keys())}"
            )
        
        model = self._models[profile]
        max_tokens = max_tokens or self._max_tokens
        temperature = temperature or self._temperature
        
        # Emit event
        self.emit("llm_request_started", {
            "provider": self.name,
            "model": model,
            "profile": profile,
            "messages_count": len(messages)
        })
        
        # Retry logic (config dynamique selon mode test)
        max_retries, retry_delay = self._get_retry_config()
        timeout = self._get_timeout()
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Appel provider-specific
                response = self._do_complete(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Succès
                self.emit("llm_request_completed", {
                    "provider": self.name,
                    "model": model,
                    "response_length": len(response),
                    "attempts": attempt + 1
                })
                
                return response
                
            except Exception as e:
                last_exception = e
                
                # Vérifier si erreur transient (réseau, timeout, rate limit)
                if self._is_transient_error(e):
                    if attempt < self._max_retries - 1:
                        # Retry
                        self.emit("llm_request_retry", {
                            "provider": self.name,
                            "attempt": attempt + 1,
                            "error": str(e)
                        })
                        time.sleep(retry_delay * (attempt + 1))  # Backoff
                        continue
                
                # Erreur non-transient ou max retries atteint
                break
                
        # Échec après retries
        self.emit("llm_request_failed", {
            "provider": self.name,
            "model": model,
            "error": str(last_exception) if last_exception else "Unknown error",
            "attempts": max_retries
        })

        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"LLM request failed after {max_retries} attempts")
    
    def _is_transient_error(self, error: Exception) -> bool:
        """
        Détermine si erreur est transient (retry possible).
        
        Args:
            error: Exception levée
        
        Returns:
            True si transient (réseau, timeout, rate limit)
        """
        error_str = str(error).lower()
        
        # Erreurs transient typiques
        transient_keywords = [
            "timeout",
            "connection",
            "rate limit",
            "429",  # HTTP 429 Too Many Requests
            "503",  # HTTP 503 Service Unavailable
            "network",
            "temporary"
        ]
        
        return any(keyword in error_str for keyword in transient_keywords)
    
    # --- Introspection ---
    
    @property
    def models(self) -> Dict[str, str]:
        """Modèles disponibles par profil."""
        return self._models.copy()
    
    @property
    def default_model(self) -> str:
        """Modèle par défaut."""
        return self._models.get("default", "unknown")
    
    def __repr__(self) -> str:
        """Représentation string de LLMClient."""
        state = "running" if self.is_running else "stopped"
        return (
            f"{self.__class__.__name__}(state={state}, "
            f"model={self.default_model})"
        )