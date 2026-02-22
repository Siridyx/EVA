"""Tests unitaires pour LLMClient et OpenAIProvider (R-012)"""

import pytest
from eva.llm.providers.openai_provider import OpenAIProvider
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class MockTransport:
    """Transport mocké pour tests (pas d'appels réseau)."""
    
    def __init__(self, should_fail=False, fail_count=0):
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.call_count = 0
    
    def post(self, url, json, headers, timeout):
        """Simule un appel POST."""
        self.call_count += 1
        
        # Simuler échecs transient
        if self.should_fail and self.call_count <= self.fail_count:
            raise Exception("Connection timeout")
        
        # Succès
        return {
            "choices": [
                {
                    "message": {
                        "content": "Mock response from LLM"
                    }
                }
            ]
        }


@pytest.fixture
def config():
    """Fixture ConfigManager."""
    return ConfigManager()


@pytest.fixture
def event_bus():
    """Fixture EventBus."""
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def mock_transport():
    """Fixture transport mocké."""
    return MockTransport()


def test_openai_provider_init(config, event_bus, mock_transport):
    """OpenAIProvider s'initialise correctement."""
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    
    assert provider.name == "OpenAIProvider"
    assert "dev" in provider.models
    assert "default" in provider.models
    assert not provider.is_running


def test_openai_provider_requires_api_key(config, event_bus, mock_transport, monkeypatch):
    """start() nécessite OPENAI_API_KEY."""
    # Supprimer la clé
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not found"):
        provider.start()


def test_openai_provider_start_with_key(config, event_bus, mock_transport, monkeypatch):
    """start() fonctionne avec OPENAI_API_KEY."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    provider.start()
    
    assert provider.is_running
    
    provider.stop()


def test_openai_provider_complete(config, event_bus, mock_transport, monkeypatch):
    """complete() génère une réponse."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    provider.start()
    
    messages = [{"role": "user", "content": "Bonjour"}]
    response = provider.complete(messages, profile="dev")
    
    assert response == "Mock response from LLM"
    assert mock_transport.call_count == 1
    
    provider.stop()


def test_openai_provider_complete_before_start(config, event_bus, mock_transport):
    """complete() avant start() raise."""
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    
    with pytest.raises(RuntimeError, match="not started"):
        provider.complete([{"role": "user", "content": "test"}])


def test_openai_provider_invalid_profile(config, event_bus, mock_transport, monkeypatch):
    """complete() rejette profil invalide."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    provider.start()
    
    with pytest.raises(ValueError, match="Invalid profile"):
        provider.complete([{"role": "user", "content": "test"}], profile="invalid")
    
    provider.stop()


def test_openai_provider_retry_on_transient_error(config, event_bus, monkeypatch):
    """complete() retry sur erreur transient."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    # Désactiver mode test pour ce test (on veut tester les retries)
    monkeypatch.delenv("EVA_TEST_MODE", raising=False)
    
    # Transport qui fail 2 fois puis succès
    transport = MockTransport(should_fail=True, fail_count=2)
    
    provider = OpenAIProvider(config, event_bus, transport=transport)
    provider.start()
    
    messages = [{"role": "user", "content": "test"}]
    response = provider.complete(messages)
    
    # Succès après 3 tentatives (2 échecs + 1 succès)
    assert response == "Mock response from LLM"
    assert transport.call_count == 3
    
    provider.stop()


def test_openai_provider_emits_events(config, event_bus, mock_transport, monkeypatch):
    """complete() émet les bons événements."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    events = []
    for evt in ["llm_request_started", "llm_request_completed"]:
        event_bus.on(evt, lambda p, e=evt: events.append(e))
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    provider.start()
    provider.complete([{"role": "user", "content": "test"}])
    provider.stop()
    
    assert "llm_request_started" in events
    assert "llm_request_completed" in events


def test_openai_provider_models_config_driven(config, event_bus, mock_transport):
    """Modèles viennent de config.yaml."""
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    
    models = provider.models
    
    assert "dev" in models
    assert "default" in models
    # Valeurs depuis config.yaml
    assert models["dev"] == config.get("llm.models.dev")
    assert models["default"] == config.get("llm.models.default")


def test_openai_provider_repr(config, event_bus, mock_transport, monkeypatch):
    """__repr__ retourne représentation correcte."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    provider = OpenAIProvider(config, event_bus, transport=mock_transport)
    
    repr_str = repr(provider)
    assert "OpenAIProvider" in repr_str
    assert "stopped" in repr_str
    
    provider.start()
    repr_str = repr(provider)
    assert "running" in repr_str
    
    provider.stop()


def test_llm_client_test_mode_short_timeout(config, event_bus, monkeypatch):
    """LLMClient utilise timeout court en mode test."""
    from eva.llm.providers.openai_provider import OpenAIProvider
    
    # Simuler mode test
    monkeypatch.setenv("EVA_TEST_MODE", "1")
    
    llm = OpenAIProvider(config, event_bus)
    
    # Timeout doit être court (0.5s)
    assert llm._get_timeout() == 0.5


def test_llm_client_test_mode_no_retries(config, event_bus, monkeypatch):
    """LLMClient n'a pas de retry en mode test."""
    from eva.llm.providers.openai_provider import OpenAIProvider
    
    # Simuler mode test
    monkeypatch.setenv("EVA_TEST_MODE", "1")
    
    llm = OpenAIProvider(config, event_bus)
    
    # Retries = 0
    max_retries, retry_delay = llm._get_retry_config()
    assert max_retries == 1
    assert retry_delay < 0.1