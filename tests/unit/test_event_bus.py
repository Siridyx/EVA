"""Tests unitaires pour EventBus (R-004)"""

import pytest
from eva.core.event_bus import EventBus


def test_eventbus_init():
    """EventBus s'initialise correctement."""
    bus = EventBus()
    assert bus.events() == []
    assert repr(bus) == "EventBus(events=0, total_handlers=0)"


def test_on_registers_handler():
    """on() enregistre un handler."""
    bus = EventBus()
    called = []
    
    def handler(payload):
        called.append(payload)
    
    bus.on("test_event", handler)
    
    assert "test_event" in bus.events()
    assert bus.handler_count("test_event") == 1


def test_emit_calls_handler():
    """emit() appelle les handlers enregistrés."""
    bus = EventBus()
    results = []
    
    def handler(payload):
        results.append(payload.get("value"))
    
    bus.on("test", handler)
    bus.emit("test", {"value": 42})
    
    assert results == [42]


def test_emit_multiple_handlers():
    """emit() appelle tous les handlers dans l'ordre."""
    bus = EventBus()
    order = []
    
    bus.on("test", lambda p: order.append(1))
    bus.on("test", lambda p: order.append(2))
    bus.on("test", lambda p: order.append(3))
    
    bus.emit("test")
    
    assert order == [1, 2, 3]


def test_emit_with_no_handlers():
    """emit() sur événement sans handler ne crash pas."""
    bus = EventBus()
    bus.emit("unknown_event", {"data": "test"})  # Pas d'erreur


def test_emit_isolates_handler_errors():
    """Si un handler crash, les autres continuent."""
    bus = EventBus()
    results = []
    
    def good_handler_1(p):
        results.append("good1")
    
    def bad_handler(p):
        raise ValueError("Handler error")
    
    def good_handler_2(p):
        results.append("good2")
    
    bus.on("test", good_handler_1)
    bus.on("test", bad_handler)
    bus.on("test", good_handler_2)
    
    bus.emit("test")
    
    # Les deux bons handlers ont été appelés malgré l'erreur
    assert results == ["good1", "good2"]


def test_off_removes_specific_handler():
    """off() retire un handler spécifique."""
    bus = EventBus()
    
    def handler1(p):
        pass
    
    def handler2(p):
        pass
    
    bus.on("test", handler1)
    bus.on("test", handler2)
    
    assert bus.handler_count("test") == 2
    
    bus.off("test", handler1)
    
    assert bus.handler_count("test") == 1


def test_off_removes_all_handlers():
    """off() sans handler retire tous les handlers."""
    bus = EventBus()
    
    bus.on("test", lambda p: None)
    bus.on("test", lambda p: None)
    
    assert bus.handler_count("test") == 2
    
    bus.off("test")
    
    assert bus.handler_count("test") == 0
    assert "test" not in bus.events()


def test_off_on_nonexistent_event():
    """off() sur événement inexistant ne crash pas."""
    bus = EventBus()
    bus.off("nonexistent")  # Pas d'erreur


def test_handler_count():
    """handler_count() retourne le bon nombre."""
    bus = EventBus()
    
    assert bus.handler_count("test") == 0
    
    bus.on("test", lambda p: None)
    assert bus.handler_count("test") == 1
    
    bus.on("test", lambda p: None)
    assert bus.handler_count("test") == 2


def test_clear_removes_all():
    """clear() supprime tous les handlers."""
    bus = EventBus()
    
    bus.on("event1", lambda p: None)
    bus.on("event2", lambda p: None)
    
    assert len(bus.events()) == 2
    
    bus.clear()
    
    assert len(bus.events()) == 0


def test_emit_requires_dict_payload():
    """emit() valide que payload est un dict."""
    bus = EventBus()
    
    with pytest.raises(TypeError, match="Payload must be dict"):
        bus.emit("test", "not a dict")


def test_on_requires_callable():
    """on() valide que handler est callable."""
    bus = EventBus()
    
    with pytest.raises(TypeError, match="Handler must be callable"):
        bus.on("test", "not a function")


def test_payload_default_empty_dict():
    """Si payload omis, {} est utilisé par défaut."""
    bus = EventBus()
    received = []
    
    def handler(payload):
        received.append(payload)
    
    bus.on("test", handler)
    bus.emit("test")
    
    assert received == [{}]


@pytest.mark.parametrize("event,handlers_count", [
    ("event_a", 1),
    ("event_b", 3),
    ("event_c", 0),
])
def test_multiple_events(event, handlers_count):
    """Plusieurs événements coexistent indépendamment."""
    bus = EventBus()
    
    for _ in range(handlers_count):
        bus.on(event, lambda p: None)
    
    assert bus.handler_count(event) == handlers_count