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

        # Override modèles avec les modèles OpenAI
        openai_models = self.get_config("llm.openai.models", None)
        if openai_models:
            self._models = openai_models
        else:
            openai_keywords = ("gpt", "o1", "o3", "o4", "davinci", "text-")
            current = self._models
            looks_like_openai = any(
                any(kw in str(v).lower() for kw in openai_keywords)
                for v in current.values()
            )
            if not looks_like_openai:
                self._models = {
                    "dev": "gpt-4o-mini",
                    "default": "gpt-4o",
                }

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
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None
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
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"OpenAIProvider: format réponse inattendu : {exc}"
            ) from exc

        content = (content or "").strip()
        if not content:
            raise ValueError("OpenAIProvider: réponse vide.")

        return content

    def stream(
        self,
        messages: List[Dict[str, str]],
        profile: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        """
        Stream les tokens depuis OpenAI via SSE.

        Yields:
            Chaque fragment de texte.

        Raises:
            RuntimeError: Si provider non démarré.
            ValueError: Si aucun token reçu.
        """
        import json as _json

        if not self.is_running:
            raise RuntimeError("OpenAIProvider not running. Call start() first.")

        if profile not in self._models:
            profile = "default"
        model = self._models.get(profile, self._models.get("default", "gpt-4o-mini"))

        max_tok = max_tokens or self._max_tokens
        temp = temperature if temperature is not None else self._temperature
        timeout = self._timeout

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tok,
            "temperature": temp,
            "stream": True,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        url = f"{self.API_BASE_URL}/chat/completions"
        received_any = False

        if self._transport is not None:
            resp = self._transport.post(
                url, json=payload, headers=headers, timeout=timeout, stream=True
            )
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line if isinstance(line, str) else line.decode("utf-8")
                if not line_str.startswith("data: "):
                    continue
                json_str = line_str[6:]
                if json_str.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(json_str)
                    text = chunk["choices"][0]["delta"].get("content", "")
                    if text:
                        received_any = True
                        yield text
                except (KeyError, IndexError, _json.JSONDecodeError):
                    continue
        else:
            response = requests.post(
                url, json=payload, headers=headers, timeout=timeout, stream=True
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if not line_str.startswith("data: "):
                    continue
                json_str = line_str[6:]
                if json_str.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(json_str)
                    text = chunk["choices"][0]["delta"].get("content", "")
                    if text:
                        received_any = True
                        yield text
                except (KeyError, IndexError, _json.JSONDecodeError):
                    continue

        if not received_any:
            raise ValueError("OpenAIProvider.stream() : reponse vide.")