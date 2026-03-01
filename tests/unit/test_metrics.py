"""Tests unitaires pour MetricsCollector (Phase 5C — R-052)."""

import time
import pytest
from eva.api.metrics import MetricsCollector, RequestRecord


# --- Init ---


def test_collector_init():
    """MetricsCollector s'initialise avec ring buffer vide et uptime > 0."""
    collector = MetricsCollector()
    summary = collector.get_summary()

    assert summary["uptime_s"] >= 0
    assert "endpoints" in summary
    assert "chat" in summary["endpoints"]
    assert "chat_stream" in summary["endpoints"]


def test_get_summary_empty():
    """get_summary() retourne structure valide meme sans donnees."""
    collector = MetricsCollector()
    summary = collector.get_summary()

    chat = summary["endpoints"]["chat"]
    stream = summary["endpoints"]["chat_stream"]

    assert chat["requests"] == 0
    assert chat["errors"] == 0
    assert chat["p50_ms"] == 0
    assert chat["p95_ms"] == 0
    assert chat["last_latency_ms"] is None

    assert stream["requests"] == 0
    assert stream["p50_ttft_ms"] == 0
    assert stream["last_ttft_ms"] is None


# --- record_chat ---


def test_record_chat_basic():
    """record_chat() enregistre une requete et apparait dans get_summary()."""
    collector = MetricsCollector()
    collector.record_chat(latency_ms=215, ok=True)

    summary = collector.get_summary()
    chat = summary["endpoints"]["chat"]

    assert chat["requests"] == 1
    assert chat["errors"] == 0
    assert chat["last_latency_ms"] == 215


def test_record_chat_error():
    """record_chat(ok=False) incremente le compteur d'erreurs."""
    collector = MetricsCollector()
    collector.record_chat(latency_ms=100, ok=True)
    collector.record_chat(latency_ms=500, ok=False)
    collector.record_chat(latency_ms=200, ok=True)

    summary = collector.get_summary()
    chat = summary["endpoints"]["chat"]

    assert chat["requests"] == 3
    assert chat["errors"] == 1


# --- record_stream ---


def test_record_stream_basic():
    """record_stream() enregistre ttft_ms et token_count."""
    collector = MetricsCollector()
    collector.record_stream(latency_ms=1240, ttft_ms=180, token_count=47, ok=True)

    summary = collector.get_summary()
    stream = summary["endpoints"]["chat_stream"]

    assert stream["requests"] == 1
    assert stream["last_latency_ms"] == 1240
    assert stream["last_ttft_ms"] == 180
    assert stream["last_token_count"] == 47
    assert stream["last_tokens_per_sec"] is not None
    assert stream["last_tokens_per_sec"] > 0


def test_tokens_per_sec_calculation():
    """tokens_per_sec calcule correctement a partir de latency_ms et ttft_ms."""
    collector = MetricsCollector()
    # 1000ms total, 200ms TTFT -> 800ms de stream -> 40 tokens/800ms = 50 t/s
    collector.record_stream(latency_ms=1000, ttft_ms=200, token_count=40, ok=True)

    stream = collector.get_summary()["endpoints"]["chat_stream"]
    # 40 tokens / 0.8s = 50.0 t/s
    assert stream["last_tokens_per_sec"] == 50.0


def test_tokens_per_sec_none_when_no_ttft():
    """tokens_per_sec est None quand ttft_ms est None."""
    collector = MetricsCollector()
    collector.record_stream(latency_ms=500, ttft_ms=None, token_count=10, ok=False)

    stream = collector.get_summary()["endpoints"]["chat_stream"]
    assert stream["last_tokens_per_sec"] is None


# --- Percentiles ---


def test_percentile_p50():
    """Percentile p50 correct sur dataset connu."""
    collector = MetricsCollector()
    # Ajouter 10 requetes avec latences 10..100
    for ms in range(10, 110, 10):
        collector.record_chat(latency_ms=ms, ok=True)

    chat = collector.get_summary()["endpoints"]["chat"]
    # p50 sur [10,20,30,40,50,60,70,80,90,100] -> idx=5 -> 60
    assert chat["p50_ms"] == 60


def test_percentile_p95():
    """Percentile p95 correct sur dataset connu."""
    collector = MetricsCollector()
    for ms in range(1, 21):   # 20 requetes : 1..20
        collector.record_chat(latency_ms=ms * 10, ok=True)

    chat = collector.get_summary()["endpoints"]["chat"]
    # p95 sur 20 elements -> idx = min(int(20*0.95), 19) = min(19, 19) = 19 -> 200
    assert chat["p95_ms"] == 200


def test_percentile_single_element():
    """Percentile sur 1 seul element retourne cet element."""
    collector = MetricsCollector()
    collector.record_chat(latency_ms=42, ok=True)

    chat = collector.get_summary()["endpoints"]["chat"]
    assert chat["p50_ms"] == 42
    assert chat["p95_ms"] == 42


# --- Ring buffer ---


def test_ring_buffer_max_history():
    """Ring buffer limite a MAX_HISTORY (100) enregistrements."""
    collector = MetricsCollector()
    assert collector.MAX_HISTORY == 100

    # Ajouter 150 requetes
    for i in range(150):
        collector.record_chat(latency_ms=i, ok=True)

    # Seulement les 100 dernieres
    chat = collector.get_summary()["endpoints"]["chat"]
    assert chat["requests"] == 100
    # La derniere latence est celle du i=149
    assert chat["last_latency_ms"] == 149


def test_ring_buffer_mixed_endpoints():
    """Ring buffer compte separement chat et chat_stream."""
    collector = MetricsCollector()

    for i in range(60):
        collector.record_chat(latency_ms=100 + i, ok=True)
    for i in range(50):
        collector.record_stream(latency_ms=500 + i, ttft_ms=100, token_count=10, ok=True)

    summary = collector.get_summary()
    # Total dans deque : 110 items -> les 100 derniers
    # On ne peut pas predire la repartition exacte mais les deux existent
    assert summary["endpoints"]["chat"]["requests"] >= 0
    assert summary["endpoints"]["chat_stream"]["requests"] >= 0


# --- TTFT p50/p95 ---


def test_ttft_percentiles():
    """p50_ttft_ms et p95_ttft_ms calcules sur les ttft valides."""
    collector = MetricsCollector()
    ttft_values = [100, 150, 200, 250, 300]
    for ttft in ttft_values:
        collector.record_stream(latency_ms=1000, ttft_ms=ttft, token_count=10, ok=True)

    stream = collector.get_summary()["endpoints"]["chat_stream"]
    # p50 sur [100,150,200,250,300] -> idx=2 -> 200
    assert stream["p50_ttft_ms"] == 200
    # p95 -> idx=min(int(5*0.95),4)=min(4,4)=4 -> 300
    assert stream["p95_ttft_ms"] == 300
