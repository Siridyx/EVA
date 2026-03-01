"""
GeminiProvider -- Provider Google Gemini pour LLMClient

Implemente l'interface LLMClient pour Google Gemini API (REST v1beta).
Aucune dependance SDK externe : utilise requests (core dep EVA).

Endpoint :
    Non-streaming : POST /v1beta/models/{model}:generateContent?key=...
    Streaming SSE : POST /v1beta/models/{model}:streamGenerateContent?alt=sse&key=...

Format messages :
    OpenAI {"role": "user/assistant/system"} -> Gemini {"role": "user/model"} + system_instruction

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


class GeminiProvider(LLMClient):
    """
    Provider Google Gemini pour LLMClient.

    Communique avec Gemini API v1beta via REST + requests.
    Aucune dependance SDK externe (google-generativeai non requis).

    Architecture :
        - API key depuis .env (GEMINI_API_KEY)
        - Conversion messages OpenAI -> format Gemini
        - Support streaming via SSE (alt=sse)
        - Transport injectable : mockable pour tests

    Modeles par defaut :
        dev     : gemini-2.0-flash   (rapide, economique)
        default : gemini-2.0-flash   (meme modele -- a ajuster si gemini-pro disponible)

    Usage:
        provider = GeminiProvider(config, bus)
        provider.start()
        response = provider.complete(messages, profile="dev")
    """

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        name: Optional[str] = None,
        transport: Optional[Any] = None,
    ) -> None:
        """
        Initialise GeminiProvider.

        Les modeles Gemini sont lus depuis llm.gemini.models (config.yaml).
        Fallback sur les valeurs par defaut ci-dessus si absent.

        Args:
            config: ConfigManager
            event_bus: EventBus
            name: Nom du composant (defaut: "GeminiProvider")
            transport: Transport HTTP injectable (pour tests)
        """
        super().__init__(config, event_bus, name or "GeminiProvider", transport=transport)

        # Override des modeles avec les modeles Gemini
        # Priorite : llm.gemini.models > llm.models > defaut Gemini
        gemini_models = self.get_config("llm.gemini.models", None)
        if gemini_models:
            self._models = gemini_models
        else:
            # Conserver les modeles config uniquement s'ils ressemblent a Gemini
            # Sinon utiliser les defauts Gemini
            current = self._models
            looks_like_gemini = any(
                "gemini" in str(v).lower() for v in current.values()
            )
            if not looks_like_gemini:
                self._models = {
                    "dev": "gemini-2.0-flash",
                    "default": "gemini-2.0-flash",
                }

        self._api_key: Optional[str] = None

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    def _do_start(self) -> None:
        """
        Charge l'API key depuis les secrets.

        Raises:
            RuntimeError: Si GEMINI_API_KEY absent du .env
        """
        self._api_key = self.get_secret("GEMINI_API_KEY")

        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not found in environment. "
                "Add it to .env file : GEMINI_API_KEY=<votre_cle>"
            )

        self.emit("gemini_provider_started", {"models": self.models})

    def _do_stop(self) -> None:
        """Arrete le provider."""
        self.emit("gemini_provider_stopped", {})

    # ---------------------------------------------------------------------------
    # Conversion messages OpenAI -> format Gemini
    # ---------------------------------------------------------------------------

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple:
        """
        Convertit le format OpenAI messages vers le format Gemini.

        Differences cles :
            - role "assistant" -> "model" (terminologie Gemini)
            - role "system"    -> system_instruction (champ separe)
            - "parts" : liste de dicts {"text": "..."}

        Args:
            messages: Liste de messages {"role": "...", "content": "..."}

        Returns:
            (system_instruction, contents)
            system_instruction : dict ou None si aucun message system
            contents           : liste de dicts Gemini-format
        """
        system_parts: List[Dict[str, str]] = []
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_parts.append({"text": content})
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                # Gemini utilise "model" pour les reponses de l'assistant
                contents.append({"role": "model", "parts": [{"text": content}]})

        system_instruction: Optional[Dict[str, Any]] = (
            {"parts": system_parts} if system_parts else None
        )
        return system_instruction, contents

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
        Generation via Gemini API (non-streaming).

        Endpoint : POST /v1beta/models/{model}:generateContent?key={key}

        Args:
            messages: Historique conversation (format OpenAI)
            model: Nom du modele Gemini (ex: "gemini-2.0-flash")
            max_tokens: Limite tokens sortie
            temperature: Temperature generation
            tools: Ignore (tool calling Gemini = Phase future)

        Returns:
            Texte genere par Gemini (strip).

        Raises:
            ValueError: Si reponse vide ou format inattendu.
            Exception: Si erreur HTTP.
        """
        system_instruction, contents = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system_instruction:
            payload["system_instruction"] = system_instruction

        url = f"{self.API_BASE}/{model}:generateContent"
        params = {"key": self._api_key}
        headers = {"Content-Type": "application/json"}
        timeout = self._get_timeout()

        if self._transport:
            # Mode test -- transport mock
            response_data = self._transport.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                params=params,
            )
        else:
            # Mode production -- requests
            import requests as req

            response = req.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                params=params,
            )
            response.raise_for_status()
            response_data = response.json()

        # Extraire le texte depuis la structure Gemini
        try:
            text = (
                response_data["candidates"][0]["content"]["parts"][0]["text"]
            )
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"GeminiProvider: format reponse inattendu : {exc}"
            ) from exc

        text = text.strip()
        if not text:
            raise ValueError("GeminiProvider: reponse vide.")

        return text

    # ---------------------------------------------------------------------------
    # Streaming SSE
    # ---------------------------------------------------------------------------

    def stream(
        self,
        messages: List[Dict[str, str]],
        profile: str = "default",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """
        Stream les tokens depuis Gemini via SSE.

        Endpoint : POST /v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}

        Chaque chunk SSE (prefixe "data: ") contient un objet JSON Gemini.
        Le texte partiel est extrait de candidates[0].content.parts[0].text.

        Args:
            messages: Historique conversation (format OpenAI)
            profile: Profil modele ("dev" ou "default")
            max_tokens: Override max_tokens
            temperature: Override temperature

        Yields:
            Chaque fragment de texte retourne par Gemini.

        Raises:
            RuntimeError: Si provider non demarre.
            ValueError: Si aucun token recu.
        """
        if not self.is_running:
            raise RuntimeError("GeminiProvider not running. Call start() first.")

        if profile not in self._models:
            profile = "default"
        model = self._models.get(profile, self._models.get("default", "gemini-2.0-flash"))

        max_tok = max_tokens or self._max_tokens
        temp = temperature if temperature is not None else self._temperature
        timeout = self._get_timeout()

        system_instruction, contents = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tok,
                "temperature": temp,
            },
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        url = f"{self.API_BASE}/{model}:streamGenerateContent"
        params = {"alt": "sse", "key": self._api_key}
        headers = {"Content-Type": "application/json"}

        received_any = False

        if self._transport is not None:
            # Mode test -- transport mock avec stream=True
            resp = self._transport.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                params=params,
                stream=True,
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
                    text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                    if text:
                        received_any = True
                        yield text
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
        else:
            # Mode production -- requests SSE
            import requests as req

            with req.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                params=params,
                stream=True,
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
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            received_any = True
                            yield text
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue

        if not received_any:
            raise ValueError("GeminiProvider.stream() : reponse vide.")
