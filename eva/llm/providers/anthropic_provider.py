"""
AnthropicProvider -- Provider Anthropic (Claude) pour LLMClient

L'API Anthropic Messages a un format different d'OpenAI :
    - system : champ top-level (pas dans messages)
    - messages : uniquement role user/assistant
    - reponse : content[0].text
    - streaming : SSE avec event: content_block_delta / delta.text

Endpoint : https://api.anthropic.com/v1/messages
Auth     : x-api-key: <ANTHROPIC_API_KEY> + anthropic-version: 2023-06-01
Cle API  : variable ANTHROPIC_API_KEY dans .env

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


class AnthropicProvider(LLMClient):
    """
    Provider Anthropic (Claude) pour LLMClient.

    Utilise l'API Anthropic Messages v1 via requests (pas de SDK anthropic).

    Architecture :
        - API key : ANTHROPIC_API_KEY depuis .env
        - Conversion messages : system extrait en champ top-level
        - Streaming : SSE Anthropic (content_block_delta events)
        - Transport injectable : mockable pour tests

    Modeles disponibles :
        dev     : claude-haiku-4-5-20251001   (rapide, economique)
        default : claude-sonnet-4-6           (puissant, equilibre)

    Usage:
        provider = AnthropicProvider(config, bus)
        provider.start()
        response = provider.complete(messages, profile="default")
    """

    API_BASE = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None,
    ) -> None:
        """
        Initialise AnthropicProvider.

        Les modeles sont lus depuis llm.anthropic.models (config.yaml).
        Fallback sur les modeles Claude par defaut si absent.

        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant (defaut: "AnthropicProvider")
            transport: Transport HTTP injectable (pour tests)
        """
        super().__init__(config, event_bus, name or "AnthropicProvider", transport=transport)

        # Override modeles avec les modeles Claude
        anthropic_models = self.get_config("llm.anthropic.models", None)
        if anthropic_models:
            self._models = anthropic_models
        else:
            current = self._models
            looks_like_claude = any(
                "claude" in str(v).lower() for v in current.values()
            )
            if not looks_like_claude:
                self._models = {
                    "dev": "claude-haiku-4-5-20251001",
                    "default": "claude-sonnet-4-6",
                }

        self._api_key: Optional[str] = None

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    def _do_start(self) -> None:
        """
        Charge l'API key depuis les secrets.

        Raises:
            RuntimeError: Si ANTHROPIC_API_KEY absent du .env
        """
        self._api_key = self.get_secret("ANTHROPIC_API_KEY")

        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Add it to .env file : ANTHROPIC_API_KEY=sk-ant-..."
            )

        self.emit("anthropic_provider_started", {"models": self.models})

    def _do_stop(self) -> None:
        """Arrete le provider."""
        self.emit("anthropic_provider_stopped", {})

    # ---------------------------------------------------------------------------
    # Conversion messages OpenAI -> format Anthropic
    # ---------------------------------------------------------------------------

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple:
        """
        Convertit le format OpenAI messages vers le format Anthropic Messages API.

        Differences cles :
            - role "system" -> champ top-level "system" (pas dans messages)
            - role "user"   -> {"role": "user", "content": "..."}
            - role "assistant" -> {"role": "assistant", "content": "..."}
            - Messages user/assistant sont concatenes (pas de system dans la liste)

        Args:
            messages: Liste de messages {"role": "...", "content": "..."}

        Returns:
            (system_text, anthropic_messages)
            system_text : str ou None
            anthropic_messages : liste de dicts Anthropic-format
        """
        system_parts: List[str] = []
        anthropic_messages: List[Dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                # Anthropic accepte "user" et "assistant" directement
                anthropic_messages.append({"role": role, "content": content})

        system_text: Optional[str] = "\n\n".join(system_parts) if system_parts else None
        return system_text, anthropic_messages

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
        Generation via Anthropic Messages API (non-streaming).

        Endpoint : POST /v1/messages

        Args:
            messages: Historique conversation (format OpenAI)
            model: Nom du modele Claude (ex: "claude-sonnet-4-6")
            max_tokens: Limite tokens sortie
            temperature: Temperature generation
            tools: Ignore (tool calling Anthropic = Phase future)

        Returns:
            Texte genere (content[0].text).

        Raises:
            ValueError: Si reponse vide ou format inattendu.
            Exception: Si erreur HTTP.
        """
        system_text, anthropic_messages = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }

        if system_text:
            payload["system"] = system_text

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
        }

        url = f"{self.API_BASE}/messages"
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

        # Format Anthropic : {"content": [{"type": "text", "text": "..."}]}
        try:
            text = response_data["content"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"AnthropicProvider: format reponse inattendu : {exc}"
            ) from exc

        text = (text or "").strip()
        if not text:
            raise ValueError("AnthropicProvider: reponse vide.")

        return text

    # ---------------------------------------------------------------------------
    # Streaming SSE Anthropic
    # ---------------------------------------------------------------------------

    def stream(
        self,
        messages: List[Dict[str, str]],
        profile: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """
        Stream les tokens depuis Anthropic via SSE.

        Format SSE Anthropic (simplifie) :
            event: content_block_delta
            data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}

        On filtre uniquement les events "content_block_delta" avec delta.type="text_delta".
        Les autres events (message_start, content_block_start, etc.) sont ignores.

        Args:
            messages: Historique conversation (format OpenAI)
            profile: Profil modele ("dev" ou "default")
            max_tokens: Override max_tokens
            temperature: Override temperature

        Yields:
            Chaque fragment de texte retourne par Claude.

        Raises:
            RuntimeError: Si provider non demarre.
            ValueError: Si aucun token recu.
        """
        if not self.is_running:
            raise RuntimeError("AnthropicProvider not running. Call start() first.")

        if profile not in self._models:
            profile = "default"
        model = self._models.get(
            profile, self._models.get("default", "claude-sonnet-4-6")
        )

        max_tok = max_tokens or self._max_tokens
        temp = temperature if temperature is not None else self._temperature
        timeout = self._get_timeout()

        system_text, anthropic_messages = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tok,
            "temperature": temp,
            "messages": anthropic_messages,
            "stream": True,
        }

        if system_text:
            payload["system"] = system_text

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
        }

        url = f"{self.API_BASE}/messages"
        received_any = False

        def _extract_text(line_str: str) -> Optional[str]:
            """Extrait le texte d'une ligne SSE content_block_delta, ou None."""
            if not line_str.startswith("data: "):
                return None
            json_str = line_str[6:]
            try:
                chunk = json.loads(json_str)
                if chunk.get("type") != "content_block_delta":
                    return None
                delta = chunk.get("delta", {})
                if delta.get("type") != "text_delta":
                    return None
                return delta.get("text") or None
            except (json.JSONDecodeError, KeyError):
                return None

        if self._transport is not None:
            resp = self._transport.post(
                url, json=payload, headers=headers, timeout=timeout, stream=True
            )
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line if isinstance(line, str) else line.decode("utf-8")
                text = _extract_text(line_str)
                if text:
                    received_any = True
                    yield text
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
                    text = _extract_text(line_str)
                    if text:
                        received_any = True
                        yield text

        if not received_any:
            raise ValueError("AnthropicProvider.stream() : reponse vide.")
