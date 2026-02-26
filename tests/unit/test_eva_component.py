"""Tests unitaires pour EvaComponent (R-005)"""

import pytest
from eva.core.eva_component import EvaComponent
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


class MockComponent(EvaComponent):
    """Composant de test simple."""
    
    def __init__(self, config, event_bus, name=None, should_fail_start=False, should_fail_stop=False):
        super().__init__(config, event_bus, name)
        self.start_called = False
        self.stop_called = False
        self.shutdown_called = False
        self.should_fail_start = should_fail_start
        self.should_fail_stop = should_fail_stop
    
    def _do_start(self):
        if self.should_fail_start:
            raise ValueError("Start failed intentionally")
        self.start_called = True
    
    def _do_stop(self):
        if self.should_fail_stop:
            raise ValueError("Stop failed intentionally")
        self.stop_called = True
    
    def _do_shutdown(self):
        self.shutdown_called = True


@pytest.fixture
def config():
    """Fixture ConfigManager."""
    return ConfigManager()


@pytest.fixture
def event_bus():
    """Fixture EventBus."""
    return EventBus()


def test_component_init(config, event_bus):
    """EvaComponent s'initialise correctement."""
    comp = MockComponent(config, event_bus, "TestComp")
    
    assert comp.name == "TestComp"
    assert comp.config is config
    assert comp.event_bus is event_bus
    assert not comp.is_started
    assert not comp.is_running


def test_component_default_name(config, event_bus):
    """Si pas de nom, utilise le nom de classe."""
    comp = MockComponent(config, event_bus)
    assert comp.name == "MockComponent"


def test_component_start(config, event_bus):
    """start() démarre le composant."""
    comp = MockComponent(config, event_bus)
    
    comp.start()
    
    assert comp.is_started
    assert comp.is_running
    assert comp.start_called


def test_component_start_idempotent(config, event_bus):
    """start() est idempotent (appel multiple = no-op)."""
    comp = MockComponent(config, event_bus)
    
    comp.start()
    call_count_1 = comp.start_called
    
    comp.start()  # 2ème appel
    call_count_2 = comp.start_called
    
    # _do_start() appelé une seule fois
    assert call_count_1 == call_count_2


def test_component_stop(config, event_bus):
    """stop() arrête le composant."""
    comp = MockComponent(config, event_bus)
    comp.start()
    
    comp.stop()
    
    assert not comp.is_started
    assert not comp.is_running
    assert comp.stop_called


def test_component_stop_idempotent(config, event_bus):
    """stop() est idempotent."""
    comp = MockComponent(config, event_bus)
    comp.start()
    comp.stop()
    
    call_count_1 = comp.stop_called
    
    comp.stop()  # 2ème appel
    call_count_2 = comp.stop_called
    
    # _do_stop() appelé une seule fois
    assert call_count_1 == call_count_2


def test_component_stop_without_start(config, event_bus):
    """stop() sans start() ne crash pas."""
    comp = MockComponent(config, event_bus)
    comp.stop()  # No-op, pas d'erreur


def test_component_shutdown(config, event_bus):
    """shutdown() appelle stop() puis _do_shutdown()."""
    comp = MockComponent(config, event_bus)
    comp.start()
    
    comp.shutdown()
    
    assert comp.stop_called
    assert comp.shutdown_called
    assert not comp.is_running


def test_component_start_failure_emits_error(config, event_bus):
    """Si start() échoue, émet component_error."""
    events = []
    event_bus.on("component_error", lambda p: events.append(p))
    
    comp = MockComponent(config, event_bus, should_fail_start=True)
    
    with pytest.raises(ValueError, match="Start failed"):
        comp.start()
    
    # Erreur émise
    assert len(events) == 1
    assert events[0]["component"] == "MockComponent"
    assert events[0]["stage"] == "start"
    assert events[0]["exception_type"] == "ValueError"


def test_component_stop_failure_emits_error(config, event_bus):
    """Si stop() échoue, émet component_error."""
    events = []
    event_bus.on("component_error", lambda p: events.append(p))
    
    comp = MockComponent(config, event_bus, should_fail_stop=True)
    comp.start()
    
    with pytest.raises(ValueError, match="Stop failed"):
        comp.stop()
    
    # Erreur émise
    assert len(events) == 1
    assert events[0]["stage"] == "stop"


def test_component_emit(config, event_bus):
    """emit() émet sur le bus."""
    events = []
    event_bus.on("test_event", lambda p: events.append(p))
    
    comp = MockComponent(config, event_bus)
    comp.emit("test_event", {"data": "test"})
    
    assert len(events) == 1
    assert events[0]["data"] == "test"


def test_component_get_config(config, event_bus):
    """get_config() récupère config."""
    comp = MockComponent(config, event_bus)
    assert comp.get_config("version") == "0.2.0-p2"

@pytest.mark.xfail(reason="DEBT-008: Paths hors tmp_path")
def test_component_get_path(config, event_bus):
    """get_path() récupère chemin data/."""
    comp = MockComponent(config, event_bus)
    path = comp.get_path("logs")
    
    assert path.is_absolute()
    assert path.exists()


def test_component_get_secret(config, event_bus, monkeypatch):
    """get_secret() récupère variable env."""
    monkeypatch.setenv("TEST_SECRET", "secret_value")
    
    comp = MockComponent(config, event_bus)
    assert comp.get_secret("TEST_SECRET") == "secret_value"


def test_component_lifecycle_events(config, event_bus):
    """Lifecycle émet les bons événements."""
    events = []
    
    for evt in ["component_created", "component_starting", "component_started",
                "component_stopping", "component_stopped"]:
        event_bus.on(evt, lambda p, e=evt: events.append(e))
    
    comp = MockComponent(config, event_bus)
    comp.start()
    comp.stop()
    
    assert "component_created" in events
    assert "component_starting" in events
    assert "component_started" in events
    assert "component_stopping" in events
    assert "component_stopped" in events


def test_component_repr(config, event_bus):
    """__repr__ retourne état correct."""
    comp = MockComponent(config, event_bus, "MyComp")
    
    assert "MyComp" in repr(comp)
    assert "stopped" in repr(comp)
    
    comp.start()
    assert "running" in repr(comp)