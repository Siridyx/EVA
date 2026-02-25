"""Tests unitaires pour OllamaProvider"""

import pytest
from eva.llm.providers.ollama_provider import OllamaProvider
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


# --- MockTransport ---

class MockTransport:
    """Transport mocké retournant une réponse valide."""

    def post(self, url, json, headers, timeout):
        return {"response": "Bonjour depuis Ollama !"}


class EmptyTransport:
    """Transport mocké retournant une réponse vide."""

    def post(self, url, json, headers, timeout):
        return {"response": ""}


class MissingFieldTransport:
    """Transport mocké sans champ 'response'."""

    def post(self, url, json, headers, timeout):
        return {"text": "mauvais champ"}


class ErrorTransport:
    """Transport mocké qui lève une exception."""

    def post(self, url, json, headers, timeout):
        raise ConnectionError("Ollama unreachable")


# --- Fixtures ---

@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def ollama(config, event_bus):
    provider = OllamaProvider(config, event_bus, transport=MockTransport())
    provider.start()
    yield provider
    provider.stop()


# --- Tests lifecycle ---

def test_ollama_provider_init(config, event_bus):
    """OllamaProvider s'initialise correctement."""
    provider = OllamaProvider(config, event_bus, transport=MockTransport())
    assert provider.name == "OllamaProvider"
    assert not provider.is_running


def test_ollama_provider_start(config, event_bus):
    """start() démarre le provider et émet l'event."""
    events = []
    event_bus.on("llm_provider_started", lambda p: events.append(p))

    provider = OllamaProvider(config, event_bus, transport=MockTransport())
    provider.start()

    assert provider.is_running
    assert len(events) == 1
    assert events[0]["provider"] == "ollama"

    provider.stop()


def test_ollama_provider_stop(config, event_bus):
    """stop() arrête le provider et émet l'event."""
    events = []
    event_bus.on("llm_provider_stopped", lambda p: events.append(p))

    provider = OllamaProvider(config, event_bus, transport=MockTransport())
    provider.start()
    provider.stop()

    assert not provider.is_running
    assert len(events) == 1
    assert events[0]["provider"] == "ollama"


def test_ollama_provider_requires_started(config, event_bus):
    """complete() lève RuntimeError si non démarré."""
    provider = OllamaProvider(config, event_bus, transport=MockTransport())

    with pytest.raises(RuntimeError, match="not started"):
        provider.complete([{"role": "user", "content": "test"}])


# --- Tests complete() ---

def test_ollama_provider_complete_basic(ollama):
    """complete() retourne la réponse du transport."""
    messages = [{"role": "user", "content": "Bonjour"}]
    response = ollama.complete(messages)

    assert response == "Bonjour depuis Ollama !"


def test_ollama_provider_complete_with_system(ollama):
    """complete() gère les messages system + user."""
    messages = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Qui es-tu ?"}
    ]
    response = ollama.complete(messages)
    assert response


def test_ollama_provider_complete_multi_turn(ollama):
    """complete() gère une conversation multi-tours."""
    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Réponse 1"},
        {"role": "user", "content": "Message 2"},
    ]
    response = ollama.complete(messages)
    assert response


def test_ollama_provider_complete_with_profile_dev(ollama):
    """complete() accepte le profil dev."""
    messages = [{"role": "user", "content": "test"}]
    response = ollama.complete(messages, profile="dev")
    assert response


def test_ollama_provider_complete_ignores_tools(ollama):
    """complete() accepte tools= et l'ignore (provider-agnostic)."""
    messages = [{"role": "user", "content": "test"}]
    tools = [{"name": "calc", "description": "calcul"}]
    response = ollama.complete(messages, tools=tools)
    assert response


# --- Tests erreurs ---

def test_ollama_provider_empty_response(config, event_bus):
    """complete() lève ValueError si réponse vide."""
    provider = OllamaProvider(config, event_bus, transport=EmptyTransport())
    provider.start()

    with pytest.raises(Exception):
        provider.complete([{"role": "user", "content": "test"}])

    provider.stop()


def test_ollama_provider_missing_response_field(config, event_bus):
    """complete() lève ValueError si champ 'response' absent."""
    provider = OllamaProvider(config, event_bus, transport=MissingFieldTransport())
    provider.start()

    with pytest.raises(Exception):
        provider.complete([{"role": "user", "content": "test"}])

    provider.stop()


# --- Tests _messages_to_prompt() ---

def test_messages_to_prompt_user_only(ollama):
    """_messages_to_prompt() formate un message utilisateur."""
    messages = [{"role": "user", "content": "Bonjour"}]
    prompt = ollama._messages_to_prompt(messages)

    assert "User: Bonjour" in prompt
    assert "Assistant:" in prompt


def test_messages_to_prompt_system_prefix(ollama):
    """_messages_to_prompt() inclut le system prompt."""
    messages = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Bonjour"},
    ]
    prompt = ollama._messages_to_prompt(messages)

    assert "Tu es EVA." in prompt
    assert "User: Bonjour" in prompt


def test_messages_to_prompt_full_conversation(ollama):
    """_messages_to_prompt() gère une conversation complète."""
    messages = [
        {"role": "system", "content": "Système"},
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "R1"},
        {"role": "user", "content": "Q2"},
    ]
    prompt = ollama._messages_to_prompt(messages)

    assert "Système" in prompt
    assert "User: Q1" in prompt
    assert "Assistant: R1" in prompt
    assert "User: Q2" in prompt
    assert prompt.endswith("Assistant:")


def test_messages_to_prompt_ignores_unknown_role(ollama):
    """_messages_to_prompt() ignore les rôles inconnus."""
    messages = [
        {"role": "tool", "content": "résultat tool"},
        {"role": "user", "content": "Suite"},
    ]
    prompt = ollama._messages_to_prompt(messages)

    # Le rôle tool est ignoré silencieusement
    assert "User: Suite" in prompt
    assert "Assistant:" in prompt
