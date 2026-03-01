"""
GroqProvider -- Provider Groq pour LLMClient

Groq expose une API compatible OpenAI : memes endpoints, meme format.
Avantage : inference ultra-rapide (LPU hardware) pour modeles open-source.

Endpoint : https://api.groq.com/openai/v1/chat/completions
Format   : identique OpenAI (choices[0].message.content)
Streaming: SSE identique OpenAI (data: {...choices:[{delta:{content:...}}]})
Auth     : Authorization: Bearer <GROQ_API>

Cle API  : variable GROQ_API dans .env

Standards :
    - Python 3.9 strict (Optional[...])
    - PEP8 strict
    - Docstrings ASCII uniquement
    - Transport mockable pour tests
"""

import json
from typing import Any, Dict, Generator, List, Optional

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.llm.llm_client import LLMClient


class GroqProvider(LLMClient):
    """
    Provider Groq pour LLMClient.

    API 100% compatible OpenAI — seuls l'endpoint et la cle different.
    Utilise requests (core dep EVA) sans SDK externe.

    Architecture :
        - API key : GROQ_API depuis .env
        - Format messages : identique OpenAI (pas de conversion)
        - Streaming : SSE OpenAI-compatible (data: JSON lines)
        - Transport injectable : mockable pour tests

    Modeles disponibles (exemple) :
        dev     : llama-3.1-8b-instant   (rapide, gratuit)
        default : llama-3.3-70b-versatile (puissant)

    Usage:
        provider = GroqProvider(config, bus)
        provider.start()
        response = provider.complete(messages, profile="dev")
    """

    API_BASE = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None,
    ) -> None:
        """
        Initialise GroqProvider.

        Les modeles sont lus depuis llm.groq.models (config.yaml).
        Fallback sur les modeles Groq par defaut si absent.

        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant (defaut: "GroqProvider")
            transport: Transport HTTP injectable (pour tests)
        """
        super().__init__(config, event_bus, name or "GroqProvider", transport=transport)

        # Override modeles avec les modeles Groq
        groq_models = self.get_config("llm.groq.models", None)
        if groq_models:
            self._models = groq_models
        else:
            current = self._models
            looks_like_groq = any(
                any(kw in str(v).lower() for kw in ("llama", "mixtral", "gemma", "groq"))
                for v in current.values()
            )
            if not looks_like_groq:
                self._models = {
                    "dev": "llama-3.1-8b-instant",
                    "default": "llama-3.3-70b-versatile",
                }

        self._api_key: Optional[str] = None

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    def _do_start(self) -> None:
        """
        Charge l'API key depuis les secrets.

        Note : la variable s'appelle GROQ_API (pas GROQ_API_KEY).

        Raises:
            RuntimeError: Si GROQ_API absent du .env
        """
        self._api_key = self.get_secret("GROQ_API")

        if not self._api_key:
            raise RuntimeError(
                "GROQ_API not found in environment. "
                "Add it to .env file : GROQ_API=gsk_..."
            )

        self.emit("groq_provider_started", {"models": self.models})

    def _do_stop(self) -> None:
        """Arrete le provider."""
        self.emit("groq_provider_stopped", {})

    # ---------------------------------------------------------------------------
    # Implementation LLMClient -- completion non-streaming
    # ---------------------------------------------------------------------------

    def _do_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generation via Groq API (non-streaming, format OpenAI).

        Endpoint : POST /openai/v1/chat/completions

        Args:
            messages: Historique conversation (format OpenAI -- passe tel quel)
            model: Nom du modele Groq (ex: "llama-3.1-8b-instant")
            max_tokens: Limite tokens sortie
            temperature: Temperature generation
            tools: Ignore (tool calling Groq = Phase future)

        Returns:
            Texte genere (choices[0].message.content).

        Raises:
            ValueError: Si reponse vide ou format inattendu.
            Exception: Si erreur HTTP.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        url = f"{self.API_BASE}/chat/completions"
        timeout = self._get_timeout()

        if self._transport:
            response_data = self._transport.post(
                url, json=payload, headers=headers, timeout=timeout
            )
        else:
            import requests as req

            response = req.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()

        # Format identique OpenAI
        try:
            text = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"GroqProvider: format reponse inattendu : {exc}"
            ) from exc

        text = (text or "").strip()
        if not text:
            raise ValueError("GroqProvider: reponse vide.")

        return text

    # ---------------------------------------------------------------------------
    # Streaming SSE (format OpenAI-compatible)
    # ---------------------------------------------------------------------------

    def stream(
        self,
        messages: List[Dict[str, str]],
        profile: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """
        Stream les tokens depuis Groq via SSE (format OpenAI-compatible).

        Chaque event SSE : data: {"choices":[{"delta":{"content":"..."}}]}
        Le dernier event : data: [DONE]

        Args:
            messages: Historique conversation (format OpenAI)
            profile: Profil modele ("dev" ou "default")
            max_tokens: Override max_tokens
            temperature: Override temperature

        Yields:
            Chaque fragment de texte retourne par Groq.

        Raises:
            RuntimeError: Si provider non demarre.
            ValueError: Si aucun token recu.
        """
        if not self.is_running:
            raise RuntimeError("GroqProvider not running. Call start() first.")

        if profile not in self._models:
            profile = "default"
        model = self._models.get(
            profile, self._models.get("default", "llama-3.1-8b-instant")
        )

        max_tok = max_tokens or self._max_tokens
        temp = temperature if temperature is not None else self._temperature
        timeout = self._get_timeout()

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

        url = f"{self.API_BASE}/chat/completions"
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
                    chunk = json.loads(json_str)
                    text = chunk["choices"][0]["delta"].get("content", "")
                    if text:
                        received_any = True
                        yield text
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
        else:
            import requests as req

            with req.post(
                url, json=payload, headers=headers, timeout=timeout, stream=True
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = (
                        line.decode("utf-8") if isinstance(line, bytes) else line
                    )
                    if not line_str.startswith("data: "):
                        continue
                    json_str = line_str[6:]
                    if json_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(json_str)
                        text = chunk["choices"][0]["delta"].get("content", "")
                        if text:
                            received_any = True
                            yield text
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue

        if not received_any:
            raise ValueError("GroqProvider.stream() : reponse vide.")
