"""Tests unitaires pour OpenAIProvider."""

import json
import pytest

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.llm.providers.openai_provider import OpenAIProvider


# ---------------------------------------------------------------------------
# Helpers -- transports mockés
# ---------------------------------------------------------------------------

def _openai_response(text: str) -> dict:
    """Construit une réponse OpenAI-compatible."""
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ]
    }


class MockTransport:
    """Transport mocké pour appels non-streaming."""

    def __init__(self, text: str = "Réponse OpenAI mockée") -> None:
        self.text = text
        self.last_call: dict = {}

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        self.last_call = {"url": url, "json": json, "headers": headers}
        return _openai_response(self.text)


class EmptyTransport:
    """Transport qui renvoie un contenu vide."""

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        return _openai_response("")


class BadFormatTransport:
    """Transport qui renvoie un format inattendu."""

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        return {"unexpected": "format"}


class StreamMockResponse:
    """Simule un objet response requests en mode stream."""

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        return iter(self._lines)


def _json(obj) -> str:
    return json.dumps(obj)


class StreamTransport:
    """Transport mocké pour appels streaming (format OpenAI SSE)."""

    def __init__(self, tokens):
        self.tokens = tokens

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        lines = []
        for token in self.tokens:
            chunk = {"choices": [{"delta": {"content": token}}]}
            lines.append(f"data: {_json(chunk)}")
        lines.append("data: [DONE]")
        return StreamMockResponse(lines)


class EmptyStreamTransport:
    """Transport streaming sans tokens."""

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        return StreamMockResponse(["data: [DONE]"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def provider(config, event_bus):
    return OpenAIProvider(config, event_bus, transport=MockTransport())


@pytest.fixture
def started_provider(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    p = OpenAIProvider(config, event_bus, transport=MockTransport())
    p.start()
    yield p
    if p.is_running:
        p.stop()


# ---------------------------------------------------------------------------
# Tests -- initialisation
# ---------------------------------------------------------------------------

def test_init_name(provider):
    assert provider.name == "OpenAIProvider"


def test_init_not_running(provider):
    assert not provider.is_running


def test_init_openai_models(provider):
    """Les modèles par défaut sont des modèles OpenAI (gpt)."""
    assert "dev" in provider.models
    assert "default" in provider.models
    dev_model = provider.models["dev"].lower()
    default_model = provider.models["default"].lower()
    assert any(kw in dev_model for kw in ("gpt", "o1", "o3", "o4", "davinci"))
    assert any(kw in default_model for kw in ("gpt", "o1", "o3", "o4", "davinci"))


def test_init_custom_name(config, event_bus):
    p = OpenAIProvider(config, event_bus, name="MonOpenAI", transport=MockTransport())
    assert p.name == "MonOpenAI"


# ---------------------------------------------------------------------------
# Tests -- lifecycle
# ---------------------------------------------------------------------------

def test_start_requires_api_key(config, event_bus, monkeypatch):
    """start() sans OPENAI_API_KEY lève RuntimeError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = OpenAIProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not found"):
        p.start()


def test_start_with_key(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider(config, event_bus, transport=MockTransport())
    p.start()
    assert p.is_running
    p.stop()


def test_stop(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider(config, event_bus, transport=MockTransport())
    p.start()
    p.stop()
    assert not p.is_running


# ---------------------------------------------------------------------------
# Tests -- complete()
# ---------------------------------------------------------------------------

def test_complete_returns_response(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    transport = MockTransport(text="Bonjour depuis OpenAI !")
    p = OpenAIProvider(config, event_bus, transport=transport)
    p.start()
    result = p.complete([{"role": "user", "content": "Dis bonjour"}])
    assert result == "Bonjour depuis OpenAI !"
    p.stop()


def test_complete_calls_openai_endpoint(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ma-cle")
    transport = MockTransport()
    p = OpenAIProvider(config, event_bus, transport=transport)
    p.start()
    p.complete([{"role": "user", "content": "Test"}])
    url = transport.last_call["url"]
    auth = transport.last_call["headers"].get("Authorization", "")
    assert "openai.com" in url
    assert "chat/completions" in url
    assert auth == "Bearer sk-ma-cle"
    p.stop()


def test_complete_not_started_raises(config, event_bus):
    p = OpenAIProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError):
        p.complete([{"role": "user", "content": "Test"}])


def test_complete_empty_response_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider(config, event_bus, transport=EmptyTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_bad_format_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider(config, event_bus, transport=BadFormatTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_passes_messages_as_is(config, event_bus, monkeypatch):
    """OpenAI reçoit les messages sans conversion."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    transport = MockTransport()
    p = OpenAIProvider(config, event_bus, transport=transport)
    p.start()
    msgs = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Salut"},
    ]
    p.complete(msgs)
    assert transport.last_call["json"]["messages"] == msgs
    p.stop()


# ---------------------------------------------------------------------------
# Tests -- stream()
# ---------------------------------------------------------------------------

def test_stream_yields_tokens(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    tokens = ["Bon", "jour", " OpenAI"]
    p = OpenAIProvider(config, event_bus, transport=StreamTransport(tokens))
    p.start()
    result = list(p.stream([{"role": "user", "content": "Salut"}]))
    assert result == tokens
    p.stop()


def test_stream_not_started_raises(config, event_bus):
    p = OpenAIProvider(config, event_bus, transport=StreamTransport([]))
    with pytest.raises(RuntimeError):
        list(p.stream([{"role": "user", "content": "Test"}]))


def test_stream_empty_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider(config, event_bus, transport=EmptyStreamTransport())
    p.start()
    with pytest.raises(ValueError):
        list(p.stream([{"role": "user", "content": "Test"}]))
    p.stop()


def test_stream_sends_stream_true(config, event_bus, monkeypatch):
    """stream() envoie stream=True dans le payload."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class CapturingTransport:
        def __init__(self):
            self.payload = {}

        def post(self, url, json=None, headers=None, timeout=None, stream=False, **kw):
            self.payload = json or {}
            chunk = {"choices": [{"delta": {"content": "ok"}}]}
            return StreamMockResponse([f"data: {_json(chunk)}", "data: [DONE]"])

    transport = CapturingTransport()
    p = OpenAIProvider(config, event_bus, transport=transport)
    p.start()
    list(p.stream([{"role": "user", "content": "Test"}]))
    assert transport.payload.get("stream") is True
    p.stop()
