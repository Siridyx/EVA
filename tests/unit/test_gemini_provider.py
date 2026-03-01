"""Tests unitaires pour GeminiProvider."""

import pytest

from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus
from eva.llm.providers.gemini_provider import GeminiProvider


# ---------------------------------------------------------------------------
# Helpers -- transports mockés
# ---------------------------------------------------------------------------

def _gemini_response(text: str) -> dict:
    """Construit une reponse Gemini non-streaming."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }


class MockTransport:
    """Transport mocke pour appels non-streaming."""

    def __init__(self, text: str = "Reponse Gemini mockee") -> None:
        self.text = text
        self.last_call: dict = {}

    def post(self, url, json=None, headers=None, timeout=None, params=None, **kwargs):
        self.last_call = {"url": url, "json": json, "params": params}
        return _gemini_response(self.text)


class EmptyTransport:
    """Transport qui renvoie un texte vide."""

    def post(self, url, json=None, headers=None, timeout=None, params=None, **kwargs):
        return _gemini_response("")


class BadFormatTransport:
    """Transport qui renvoie un format inattendu."""

    def post(self, url, json=None, headers=None, timeout=None, params=None, **kwargs):
        return {"unexpected": "format"}


class StreamMockResponse:
    """Simule un objet response requests en mode stream."""

    def __init__(self, sse_lines):
        self._lines = sse_lines

    def iter_lines(self):
        return iter(self._lines)


class StreamTransport:
    """Transport mocke pour appels streaming."""

    def __init__(self, tokens):
        self.tokens = tokens

    def post(self, url, json=None, headers=None, timeout=None, params=None, stream=False, **kwargs):
        lines = []
        for token in self.tokens:
            chunk = {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": token}],
                            "role": "model",
                        }
                    }
                ]
            }
            import json as _json
            lines.append(f"data: {_json.dumps(chunk)}")
        return StreamMockResponse(lines)


class EmptyStreamTransport:
    """Transport streaming qui ne renvoie aucun token."""

    def post(self, url, json=None, headers=None, timeout=None, params=None, stream=False, **kwargs):
        return StreamMockResponse([])


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
    """Provider avec transport mock, non demarre."""
    return GeminiProvider(config, event_bus, transport=MockTransport())


@pytest.fixture
def started_provider(config, event_bus, monkeypatch):
    """Provider demarre avec cle API mockee."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    p = GeminiProvider(config, event_bus, transport=MockTransport())
    p.start()
    yield p
    if p.is_running:
        p.stop()


# ---------------------------------------------------------------------------
# Tests -- initialisation
# ---------------------------------------------------------------------------

def test_init_name(provider):
    """GeminiProvider a le bon nom par defaut."""
    assert provider.name == "GeminiProvider"


def test_init_not_running(provider):
    """GeminiProvider n'est pas demarre apres init."""
    assert not provider.is_running


def test_init_gemini_models(provider):
    """Les modeles par defaut sont des modeles Gemini."""
    assert "dev" in provider.models
    assert "default" in provider.models
    assert "gemini" in provider.models["dev"].lower()
    assert "gemini" in provider.models["default"].lower()


def test_init_custom_name(config, event_bus):
    """GeminiProvider accepte un nom custom."""
    p = GeminiProvider(config, event_bus, name="MonGemini", transport=MockTransport())
    assert p.name == "MonGemini"


# ---------------------------------------------------------------------------
# Tests -- lifecycle
# ---------------------------------------------------------------------------

def test_start_requires_api_key(config, event_bus, monkeypatch):
    """start() sans GEMINI_API_KEY leve RuntimeError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = GeminiProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY not found"):
        p.start()


def test_start_with_key(config, event_bus, monkeypatch):
    """start() avec cle -> is_running=True."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = GeminiProvider(config, event_bus, transport=MockTransport())
    p.start()
    assert p.is_running
    p.stop()


def test_stop(config, event_bus, monkeypatch):
    """stop() -> is_running=False."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = GeminiProvider(config, event_bus, transport=MockTransport())
    p.start()
    p.stop()
    assert not p.is_running


# ---------------------------------------------------------------------------
# Tests -- conversion messages
# ---------------------------------------------------------------------------

def test_convert_messages_user_only(started_provider):
    """Messages user seuls -> contents sans system_instruction."""
    msgs = [{"role": "user", "content": "Bonjour"}]
    sys_instr, contents = started_provider._convert_messages(msgs)
    assert sys_instr is None
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "Bonjour"


def test_convert_messages_with_system(started_provider):
    """Message system -> system_instruction separe."""
    msgs = [
        {"role": "system", "content": "Tu es EVA."},
        {"role": "user", "content": "Salut"},
    ]
    sys_instr, contents = started_provider._convert_messages(msgs)
    assert sys_instr is not None
    assert sys_instr["parts"][0]["text"] == "Tu es EVA."
    assert len(contents) == 1
    assert contents[0]["role"] == "user"


def test_convert_messages_assistant_to_model(started_provider):
    """Role 'assistant' est converti en 'model'."""
    msgs = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Reponse"},
    ]
    _, contents = started_provider._convert_messages(msgs)
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"


# ---------------------------------------------------------------------------
# Tests -- complete()
# ---------------------------------------------------------------------------

def test_complete_returns_response(config, event_bus, monkeypatch):
    """complete() retourne la reponse du transport mock."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    transport = MockTransport(text="Bonjour depuis Gemini !")
    p = GeminiProvider(config, event_bus, transport=transport)
    p.start()

    msgs = [{"role": "user", "content": "Dis bonjour"}]
    result = p.complete(msgs)

    assert result == "Bonjour depuis Gemini !"
    p.stop()


def test_complete_calls_correct_endpoint(config, event_bus, monkeypatch):
    """complete() appelle l'endpoint generateContent avec la cle."""
    monkeypatch.setenv("GEMINI_API_KEY", "ma-cle-test")
    transport = MockTransport()
    p = GeminiProvider(config, event_bus, transport=transport)
    p.start()

    msgs = [{"role": "user", "content": "Test"}]
    p.complete(msgs)

    url = transport.last_call["url"]
    params = transport.last_call["params"]
    assert "generateContent" in url
    assert params["key"] == "ma-cle-test"
    p.stop()


def test_complete_not_started_raises(config, event_bus):
    """complete() sans start() leve RuntimeError."""
    p = GeminiProvider(config, event_bus, transport=MockTransport())
    with pytest.raises(RuntimeError):
        p.complete([{"role": "user", "content": "Test"}])


def test_complete_empty_response_raises(config, event_bus, monkeypatch):
    """complete() avec reponse vide leve ValueError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = GeminiProvider(config, event_bus, transport=EmptyTransport())
    p.start()

    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


def test_complete_bad_format_raises(config, event_bus, monkeypatch):
    """complete() avec format inattendu leve ValueError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = GeminiProvider(config, event_bus, transport=BadFormatTransport())
    p.start()

    with pytest.raises((ValueError, Exception)):
        p.complete([{"role": "user", "content": "Test"}])
    p.stop()


# ---------------------------------------------------------------------------
# Tests -- stream()
# ---------------------------------------------------------------------------

def test_stream_yields_tokens(config, event_bus, monkeypatch):
    """stream() yield les tokens dans l'ordre."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tokens = ["Bon", "jour", " depuis", " Gemini"]
    p = GeminiProvider(config, event_bus, transport=StreamTransport(tokens))
    p.start()

    msgs = [{"role": "user", "content": "Dis bonjour"}]
    result = list(p.stream(msgs))

    assert result == tokens
    p.stop()


def test_stream_not_started_raises(config, event_bus):
    """stream() sans start() leve RuntimeError."""
    p = GeminiProvider(config, event_bus, transport=StreamTransport([]))
    with pytest.raises(RuntimeError):
        list(p.stream([{"role": "user", "content": "Test"}]))


def test_stream_empty_raises(config, event_bus, monkeypatch):
    """stream() sans tokens leve ValueError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = GeminiProvider(config, event_bus, transport=EmptyStreamTransport())
    p.start()

    with pytest.raises(ValueError, match="reponse vide"):
        list(p.stream([{"role": "user", "content": "Test"}]))
    p.stop()


def test_stream_calls_sse_endpoint(config, event_bus, monkeypatch):
    """stream() appelle l'endpoint streamGenerateContent avec alt=sse."""
    monkeypatch.setenv("GEMINI_API_KEY", "ma-cle")

    class CapturingStreamTransport:
        def __init__(self):
            self.last_url = ""
            self.last_params = {}

        def post(self, url, json=None, headers=None, timeout=None, params=None, stream=False, **kw):
            self.last_url = url
            self.last_params = params or {}
            chunk = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
            import json as _j
            return StreamMockResponse([f"data: {_j.dumps(chunk)}"])

    transport = CapturingStreamTransport()
    p = GeminiProvider(config, event_bus, transport=transport)
    p.start()

    list(p.stream([{"role": "user", "content": "Test"}]))

    assert "streamGenerateContent" in transport.last_url
    assert transport.last_params.get("alt") == "sse"
    assert transport.last_params.get("key") == "ma-cle"
    p.stop()
