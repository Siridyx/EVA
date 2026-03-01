"""Tests unitaires pour GroqProvider."""

import json
import pytest

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.llm.providers.groq_provider import GroqProvider


# ---------------------------------------------------------------------------
# Helpers -- transports mockés
# ---------------------------------------------------------------------------

def _groq_response(text: str) -> dict:
    """Construit une reponse Groq/OpenAI-compatible."""
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ]
    }


class MockTransport:
    """Transport mocke pour appels non-streaming."""

    def __init__(self, text: str = "Reponse Groq mockee") -> None:
        self.text = text
        self.last_call: dict = {}

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        self.last_call = {"url": url, "json": json, "headers": headers}
        return _groq_response(self.text)


class EmptyTransport:
    """Transport qui renvoie un contenu vide."""

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        return _groq_response("")


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


class StreamTransport:
    """Transport mocke pour appels streaming (format OpenAI SSE)."""

    def __init__(self, tokens):
        self.tokens = tokens

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        lines = []
        for token in self.tokens:
            chunk = {"choices": [{"delta": {"content": token}}]}
            lines.append(f"data: {json_dumps(chunk)}")
        lines.append("data: [DONE]")
        return StreamMockResponse(lines)


class EmptyStreamTransport:
    """Transport streaming sans tokens."""

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        return StreamMockResponse(["data: [DONE]"])


def json_dumps(obj) -> str:
    return json.dumps(obj)


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
    return GroqProvider(config, event_bus, transport=MockTransport())


@pytest.fixture
def started_provider(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test-key")
    p = GroqProvider(config, event_bus, transport=MockTransport())
    p.start()
    yield p
    if p.is_running:
        p.stop()


# ---------------------------------------------------------------------------
# Tests -- initialisation
# ---------------------------------------------------------------------------

def test_init_name(provider):
    assert provider.name == "GroqProvider"


def test_init_not_running(provider):
    assert not provider.is_running


def test_init_groq_models(provider):
    """Les modeles par defaut sont des modeles Groq/Llama."""
    assert "dev" in provider.models
    assert "default" in provider.models
    # Groq utilise des modeles llama, mixtral ou gemma
    dev_model = provider.models["dev"].lower()
    default_model = provider.models["default"].lower()
    assert any(kw in dev_model for kw in ("llama", "mixtral", "gemma", "groq"))
    assert any(kw in default_model for kw in ("llama", "mixtral", "gemma", "groq"))


def test_init_custom_name(config, event_bus):
    p = GroqProvider(config, event_bus, name="MonGroq", transport=MockTransport())
    assert p.name == "MonGroq"


# ---------------------------------------------------------------------------
# Tests -- lifecycle
# ---------------------------------------------------------------------------

def test_start_requires_groq_api(config, event_bus, monkeypatch):
    """start() sans GROQ_API leve RuntimeError."""
    monkeypatch.delenv("GROQ_API", raising=False)
    p = GroqProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError, match="GROQ_API not found"):
        p.start()


def test_start_with_key(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    p = GroqProvider(config, event_bus, transport=MockTransport())
    p.start()
    assert p.is_running
    p.stop()


def test_stop(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    p = GroqProvider(config, event_bus, transport=MockTransport())
    p.start()
    p.stop()
    assert not p.is_running


# ---------------------------------------------------------------------------
# Tests -- complete()
# ---------------------------------------------------------------------------

def test_complete_returns_response(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    transport = MockTransport(text="Bonjour depuis Groq !")
    p = GroqProvider(config, event_bus, transport=transport)
    p.start()

    result = p.complete([{"role": "user", "content": "Dis bonjour"}])
    assert result == "Bonjour depuis Groq !"
    p.stop()


def test_complete_calls_groq_endpoint(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_ma-cle")
    transport = MockTransport()
    p = GroqProvider(config, event_bus, transport=transport)
    p.start()

    p.complete([{"role": "user", "content": "Test"}])

    url = transport.last_call["url"]
    auth = transport.last_call["headers"].get("Authorization", "")
    assert "groq.com" in url
    assert "chat/completions" in url
    assert auth == "Bearer gsk_ma-cle"
    p.stop()


def test_complete_not_started_raises(config, event_bus):
    p = GroqProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError):
        p.complete([{"role": "user", "content": "Test"}])


def test_complete_empty_response_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    p = GroqProvider(config, event_bus, transport=EmptyTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_bad_format_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    p = GroqProvider(config, event_bus, transport=BadFormatTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_passes_messages_as_is(config, event_bus, monkeypatch):
    """Groq recoit les messages OpenAI sans conversion."""
    monkeypatch.setenv("GROQ_API", "gsk_test")
    transport = MockTransport()
    p = GroqProvider(config, event_bus, transport=transport)
    p.start()

    msgs = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Salut"},
    ]
    p.complete(msgs)

    sent_messages = transport.last_call["json"]["messages"]
    assert sent_messages == msgs  # Pas de conversion pour Groq
    p.stop()


# ---------------------------------------------------------------------------
# Tests -- stream()
# ---------------------------------------------------------------------------

def test_stream_yields_tokens(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    tokens = ["Bon", "jour", " Groq"]
    p = GroqProvider(config, event_bus, transport=StreamTransport(tokens))
    p.start()

    result = list(p.stream([{"role": "user", "content": "Salut"}]))
    assert result == tokens
    p.stop()


def test_stream_not_started_raises(config, event_bus):
    p = GroqProvider(config, event_bus, transport=StreamTransport([]))
    with pytest.raises(RuntimeError):
        list(p.stream([{"role": "user", "content": "Test"}]))


def test_stream_empty_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("GROQ_API", "gsk_test")
    p = GroqProvider(config, event_bus, transport=EmptyStreamTransport())
    p.start()
    with pytest.raises(ValueError, match="reponse vide"):
        list(p.stream([{"role": "user", "content": "Test"}]))
    p.stop()


def test_stream_sends_stream_true(config, event_bus, monkeypatch):
    """stream() envoie stream=True dans le payload."""
    monkeypatch.setenv("GROQ_API", "gsk_test")

    class CapturingTransport:
        def __init__(self):
            self.payload = {}

        def post(self, url, json=None, headers=None, timeout=None, stream=False, **kw):
            self.payload = json or {}
            chunk = {"choices": [{"delta": {"content": "ok"}}]}
            return StreamMockResponse([f"data: {json_dumps(chunk)}", "data: [DONE]"])

    transport = CapturingTransport()
    p = GroqProvider(config, event_bus, transport=transport)
    p.start()

    list(p.stream([{"role": "user", "content": "Test"}]))
    assert transport.payload.get("stream") is True
    p.stop()
