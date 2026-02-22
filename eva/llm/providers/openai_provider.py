"""
OpenAIProvider — Provider OpenAI pour LLMClient

Implémentation OpenAI API avec transport injectable.

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Docstrings complètes
- Transport mockable pour tests
"""

from typing import List, Dict, Any, Optional
import requests

from eva.llm.llm_client import LLMClient
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class OpenAIProvider(LLMClient):
    """
    Provider OpenAI pour LLMClient.
    
    Implémente l'interface LLMClient pour OpenAI API.
    
    Architecture :
        - Utilise requests (ou transport injecté pour tests)
        - Timeout configuré
        - API key depuis secrets (.env)
    
    Usage:
        # Production
        provider = OpenAIProvider(config, bus)
        provider.start()
        
        # Tests (avec mock)
        mock_transport = MockTransport()
        provider = OpenAIProvider(config, bus, transport=mock_transport)
    """
    
    API_BASE_URL = "https://api.openai.com/v1"
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None
    ) -> None:
        """
        Initialise OpenAIProvider.
        
        Args:
            config: Gestionnaire de configuration
            event_bus: Bus d'événements central
            name: Nom du composant (défaut: "OpenAIProvider")
            transport: Transport injectable pour tests
        """
        super().__init__(
            config,
            event_bus,
            name or "OpenAIProvider",
            transport=transport
        )
        
        # API key (depuis .env)
        self._api_key: Optional[str] = None
    
    # --- Lifecycle ---
    
    def _do_start(self) -> None:
        """
        Démarre le provider OpenAI.
        
        Charge l'API key depuis secrets.
        
        Raises:
            RuntimeError: Si OPENAI_API_KEY absent
        """
        self._api_key = self.get_secret("OPENAI_API_KEY")
        
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found in environment. "
                "Add it to .env file."
            )
        
        self.emit("openai_provider_started", {
            "models": self.models
        })
    
    # --- Implémentation LLMClient ---
    
    def _do_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """
        Implémentation OpenAI de la complétion.
        
        Args:
            messages: Historique conversation
            model: Nom du modèle OpenAI
            max_tokens: Limite tokens
            temperature: Température
        
        Returns:
            Réponse générée
        
        Raises:
            Exception: Si erreur API
        """
        # Payload OpenAI
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        
        # Utiliser transport ou requests
        if self._transport:
            # Mode test (transport mocké)
            response_data = self._transport.post(
                f"{self.API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout
            )
        else:
            # Mode production (requests réel)
            response = requests.post(
                f"{self.API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout
            )
            response.raise_for_status()
            response_data = response.json()
        
        # Extraire réponse
        content = response_data["choices"][0]["message"]["content"]
        
        return content