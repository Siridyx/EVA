"""
OllamaProvider — Provider LLM pour Ollama (local)

Responsabilités :
- Communication avec Ollama API locale
- Support streaming (future)
- Pas besoin d'API key

Architecture :
- Hérite LLMClient
- Endpoint : http://localhost:11434/api/generate
- Format JSON simple

Standards :
- Python 3.9 strict
- PEP8 strict
"""

import json
from typing import List, Dict, Any, Optional

from eva.llm.llm_client import LLMClient
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class OllamaProvider(LLMClient):
    """
    Provider Ollama pour LLM local.
    
    Communique avec Ollama API sur localhost:11434.
    
    Usage:
        llm = OllamaProvider(config, bus)
        llm.start()
        
        messages = [{"role": "user", "content": "Bonjour"}]
        response = llm.complete(messages, profile="dev")
    """
    
    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None
    ) -> None:
        """
        Initialise OllamaProvider.
        
        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant
            transport: Transport HTTP injectable (pour tests)
        """
        super().__init__(config, event_bus, name or "OllamaProvider", transport)

        # Endpoint Ollama
        self._endpoint = self.get_config("llm.ollama.endpoint", "http://localhost:11434")
        # R-044 perf : Session HTTP réutilisée (TCP keepalive) — lazy init dans _do_complete
        self._http_session: Optional[Any] = None

    def _do_start(self) -> None:
        """Démarre le provider."""
        self.emit("llm_provider_started", {
            "provider": "ollama",
            "endpoint": self._endpoint
        })

    def _do_stop(self) -> None:
        """Arrête le provider."""
        # Fermer la Session HTTP proprement
        if self._http_session is not None:
            try:
                self._http_session.close()
            except Exception:
                pass
            self._http_session = None
        self.emit("llm_provider_stopped", {
            "provider": "ollama"
        })
    
    def _do_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Génère une complétion via Ollama.
        
        Args:
            messages: Liste de messages (format OpenAI)
            model: Nom du modèle (ex: "llama3.2:latest")
            max_tokens: Limite tokens
            temperature: Température
        
        Returns:
            Réponse générée
        
        Raises:
            Exception: Si erreur API
        """
        # Construire prompt depuis messages
        prompt = self._messages_to_prompt(messages)
        
        # Payload Ollama (format generate)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Timeout dynamique
        timeout = self._get_timeout()
        
        # Appel API
        if self._transport:
            # Mode test avec mock
            response_data = self._transport.post(
                f"{self._endpoint}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
        else:
            # Mode production — Session réutilisée (R-044 : TCP keepalive)
            import requests
            if self._http_session is None:
                self._http_session = requests.Session()

            response = self._http_session.post(
                f"{self._endpoint}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )

            response.raise_for_status()
            response_data = response.json()
        
        # Extraire réponse (format: {response: "..."})
        if "response" not in response_data:
            raise ValueError("Ollama response missing 'response' field")
        
        reply = response_data["response"].strip()
        
        if not reply:
            raise ValueError("Ollama returned empty response")
        
        return reply


    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convertit format OpenAI messages vers prompt simple.
        
        Args:
            messages: Liste de messages {"role": "...", "content": "..."}
        
        Returns:
            Prompt formaté
        """
        parts = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                parts.append(content)
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(parts)
        prompt += "\n\nAssistant:"
        
        return prompt