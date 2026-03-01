"""Tests unitaires pour AnthropicProvider."""

import json
import pytest

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.llm.providers.anthropic_provider import AnthropicProvider


# ---------------------------------------------------------------------------
# Helpers -- transports mockés
# ---------------------------------------------------------------------------

def _anthropic_response(text: str) -> dict:
    """Construit une reponse Anthropic Messages API."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "model": "claude-sonnet-4-6",
        "stop_reason": "end_turn",
    }


def _sse_content_delta(text: str) -> str:
    """Construit une ligne SSE content_block_delta."""
    chunk = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": text},
    }
    return f"data: {json.dumps(chunk)}"


class MockTransport:
    """Transport mocke pour appels non-streaming."""

    def __init__(self, text: str = "Reponse Anthropic mockee") -> None:
        self.text = text
        self.last_call: dict = {}

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        self.last_call = {"url": url, "json": json, "headers": headers}
        return _anthropic_response(self.text)


class EmptyTransport:
    """Transport qui renvoie un contenu vide."""

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        return _anthropic_response("")


class BadFormatTransport:
    """Transport qui renvoie un format inattendu."""

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        return {"unexpected": "format"}


class StreamMockResponse:
    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        return iter(self._lines)


class StreamTransport:
    """Transport mocke streaming avec format SSE Anthropic."""

    def __init__(self, tokens):
        self.tokens = tokens

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        lines = []
        # message_start (ignore)
        lines.append("event: message_start")
        lines.append('data: {"type":"message_start","message":{}}')
        # content_block_start (ignore)
        lines.append("event: content_block_start")
        lines.append('data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}')
        # tokens
        for token in self.tokens:
            lines.append("event: content_block_delta")
            lines.append(_sse_content_delta(token))
        # message_stop (ignore)
        lines.append("event: message_stop")
        lines.append('data: {"type":"message_stop"}')
        return StreamMockResponse(lines)


class EmptyStreamTransport:
    """Transport streaming sans tokens de texte."""

    def post(self, url, json=None, headers=None, timeout=None, stream=False, **kwargs):
        # Seulement des events ignores
        return StreamMockResponse([
            "event: message_start",
            '{"type":"message_start"}',
            "event: message_stop",
            '{"type":"message_stop"}',
        ])


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
    return AnthropicProvider(config, event_bus, transport=MockTransport())


@pytest.fixture
def started_provider(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=MockTransport())
    p.start()
    yield p
    if p.is_running:
        p.stop()


# ---------------------------------------------------------------------------
# Tests -- initialisation
# ---------------------------------------------------------------------------

def test_init_name(provider):
    assert provider.name == "AnthropicProvider"


def test_init_not_running(provider):
    assert not provider.is_running


def test_init_claude_models(provider):
    """Les modeles par defaut sont des modeles Claude."""
    assert "dev" in provider.models
    assert "default" in provider.models
    assert "claude" in provider.models["dev"].lower()
    assert "claude" in provider.models["default"].lower()


def test_init_custom_name(config, event_bus):
    p = AnthropicProvider(config, event_bus, name="MonClaude", transport=MockTransport())
    assert p.name == "MonClaude"


# ---------------------------------------------------------------------------
# Tests -- lifecycle
# ---------------------------------------------------------------------------

def test_start_requires_api_key(config, event_bus, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not found"):
        p.start()


def test_start_with_key(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=MockTransport())
    p.start()
    assert p.is_running
    p.stop()


def test_stop(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=MockTransport())
    p.start()
    p.stop()
    assert not p.is_running


# ---------------------------------------------------------------------------
# Tests -- conversion messages
# ---------------------------------------------------------------------------

def test_convert_messages_user_only(started_provider):
    system_text, msgs = started_provider._convert_messages(
        [{"role": "user", "content": "Bonjour"}]
    )
    assert system_text is None
    assert len(msgs) == 1
    assert msgs[0] == {"role": "user", "content": "Bonjour"}


def test_convert_messages_system_extracted(started_provider):
    """Le message system devient un champ top-level, pas dans messages."""
    system_text, msgs = started_provider._convert_messages([
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Salut"},
    ])
    assert system_text == "Tu es EVA."
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


def test_convert_messages_assistant_kept(started_provider):
    """Le role assistant est conserve tel quel (pas de conversion)."""
    _, msgs = started_provider._convert_messages([
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Reponse"},
    ])
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_convert_messages_multiple_system(started_provider):
    """Plusieurs messages system sont concatenes."""
    system_text, _ = started_provider._convert_messages([
        {"role": "system", "content": "Tu es EVA."},
        {"role": "system", "content": "Sois concis."},
        {"role": "user", "content": "Test"},
    ])
    assert "Tu es EVA." in system_text
    assert "Sois concis." in system_text


# ---------------------------------------------------------------------------
# Tests -- complete()
# ---------------------------------------------------------------------------

def test_complete_returns_response(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    transport = MockTransport(text="Bonjour depuis Claude !")
    p = AnthropicProvider(config, event_bus, transport=transport)
    p.start()

    result = p.complete([{"role": "user", "content": "Dis bonjour"}])
    assert result == "Bonjour depuis Claude !"
    p.stop()


def test_complete_calls_anthropic_endpoint(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-ma-cle")
    transport = MockTransport()
    p = AnthropicProvider(config, event_bus, transport=transport)
    p.start()

    p.complete([{"role": "user", "content": "Test"}])

    url = transport.last_call["url"]
    headers = transport.last_call["headers"]
    assert "anthropic.com" in url
    assert "/messages" in url
    assert headers.get("x-api-key") == "sk-ant-ma-cle"
    assert headers.get("anthropic-version") == "2023-06-01"
    p.stop()


def test_complete_sends_system_field(config, event_bus, monkeypatch):
    """Le system est envoye comme champ top-level, pas dans messages."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    transport = MockTransport()
    p = AnthropicProvider(config, event_bus, transport=transport)
    p.start()

    msgs = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Test"},
    ]
    p.complete(msgs)

    payload = transport.last_call["json"]
    assert payload.get("system") == "Tu es EVA."
    # Le champ messages ne doit pas contenir le system
    for m in payload["messages"]:
        assert m["role"] != "system"
    p.stop()


def test_complete_not_started_raises(config, event_bus):
    p = AnthropicProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError):
        p.complete([{"role": "user", "content": "Test"}])


def test_complete_empty_response_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=EmptyTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_bad_format_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=BadFormatTransport())
    p.start()
    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


# ---------------------------------------------------------------------------
# Tests -- stream()
# ---------------------------------------------------------------------------

def test_stream_yields_tokens(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    tokens = ["Bon", "jour", " Claude"]
    p = AnthropicProvider(config, event_bus, transport=StreamTransport(tokens))
    p.start()

    result = list(p.stream([{"role": "user", "content": "Salut"}]))
    assert result == tokens
    p.stop()


def test_stream_not_started_raises(config, event_bus):
    p = AnthropicProvider(config, event_bus, transport=StreamTransport([]))
    with pytest.raises(RuntimeError):
        list(p.stream([{"role": "user", "content": "Test"}]))


def test_stream_empty_raises(config, event_bus, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    p = AnthropicProvider(config, event_bus, transport=EmptyStreamTransport())
    p.start()
    with pytest.raises(ValueError, match="reponse vide"):
        list(p.stream([{"role": "user", "content": "Test"}]))
    p.stop()


def test_stream_ignores_non_text_events(config, event_bus, monkeypatch):
    """Les events SSE non-texte (message_start, etc.) sont ignores."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    class MixedEventsTransport:
        def post(self, url, json=None, headers=None, timeout=None, stream=False, **kw):
            lines = [
                # Event ignore
                'data: {"type":"message_start"}',
                # Event texte valide
                _sse_content_delta("Bonjour"),
                # Event ignore
                'data: {"type":"content_block_stop","index":0}',
                # Event texte valide
                _sse_content_delta(" Claude"),
                # Event ignore
                'data: {"type":"message_stop"}',
            ]
            return StreamMockResponse(lines)

    p = AnthropicProvider(config, event_bus, transport=MixedEventsTransport())
    p.start()

    result = list(p.stream([{"role": "user", "content": "Test"}]))
    assert result == ["Bonjour", " Claude"]
    p.stop()
