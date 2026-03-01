"""
MetricsCollector — Ring buffer de metriques API en memoire.

Responsabilites :
- Enregistrer latences par endpoint (ring buffer deque maxlen=100)
- Calculer p50/p95 a la demande
- Tracker TTFT (time-to-first-token) et debit tokens pour SSE
- Zero persistance disque (in-memory uniquement)

Standards :
- Python 3.9 strict (Optional[...])
- PEP8 strict
- Aucune dependance externe (stdlib uniquement)
"""

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class RequestRecord:
    """Enregistrement d'une requete API."""

    timestamp: float           # time.monotonic() au moment de l'enregistrement
    endpoint: str              # "chat" | "chat_stream"
    latency_ms: int            # Latence totale en ms
    ttft_ms: Optional[int] = None          # Time-to-first-token (streaming only)
    token_count: Optional[int] = None      # Nombre de tokens (streaming only)
    tokens_per_sec: Optional[float] = None # Debit tokens (streaming only)
    ok: bool = True            # False si erreur


class MetricsCollector:
    """
    Collecte de metriques API avec ring buffer en memoire.

    Stocke les MAX_HISTORY dernieres requetes par endpoint.
    Calcule p50/p95 a la demande (tri sur la liste).

    Usage:
        collector = MetricsCollector()

        # Enregistrement
        collector.record_chat(latency_ms=215, ok=True)
        collector.record_stream(latency_ms=1240, ttft_ms=180, token_count=47)

        # Lecture
        summary = collector.get_summary()
        # {"uptime_s": 42, "endpoints": {"chat": {...}, "chat_stream": {...}}}
    """

    MAX_HISTORY = 100

    def __init__(self) -> None:
        self._records: deque = deque(maxlen=self.MAX_HISTORY)
        self._start_time: float = time.monotonic()

    # --- Enregistrement ---

    def record_chat(self, latency_ms: int, ok: bool = True) -> None:
        """
        Enregistre une requete POST /chat.

        Args:
            latency_ms: Latence totale en millisecondes
            ok: True si succes, False si erreur
        """
        self._records.append(RequestRecord(
            timestamp=time.monotonic(),
            endpoint="chat",
            latency_ms=latency_ms,
            ok=ok,
        ))

    def record_stream(
        self,
        latency_ms: int,
        ttft_ms: Optional[int],
        token_count: int,
        ok: bool = True,
    ) -> None:
        """
        Enregistre une requete GET /chat/stream.

        Args:
            latency_ms: Latence totale en millisecondes
            ttft_ms: Time-to-first-token en ms (None si aucun token recu)
            token_count: Nombre total de tokens emis
            ok: True si succes, False si erreur
        """
        tokens_per_sec: Optional[float] = None
        if ttft_ms is not None and token_count > 0:
            stream_duration_s = (latency_ms - ttft_ms) / 1000
            if stream_duration_s > 0:
                tokens_per_sec = round(token_count / stream_duration_s, 1)

        self._records.append(RequestRecord(
            timestamp=time.monotonic(),
            endpoint="chat_stream",
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
            token_count=token_count,
            tokens_per_sec=tokens_per_sec,
            ok=ok,
        ))

    # --- Lecture ---

    def get_summary(self) -> dict:
        """
        Retourne le resume complet des metriques.

        Returns:
            Dict avec uptime_s et stats par endpoint (p50/p95, errors, last).
        """
        records = list(self._records)
        chat_records = [r for r in records if r.endpoint == "chat"]
        stream_records = [r for r in records if r.endpoint == "chat_stream"]

        return {
            "uptime_s": int(time.monotonic() - self._start_time),
            "endpoints": {
                "chat": self._endpoint_stats(chat_records),
                "chat_stream": self._stream_stats(stream_records),
            },
        }

    # --- Stats internes ---

    def _percentile(self, data: List[int], p: float) -> int:
        """
        Calcule le percentile p (0.0 - 1.0) d'une liste d'entiers.

        Retourne 0 si data vide.
        """
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = min(int(len(sorted_data) * p), len(sorted_data) - 1)
        return sorted_data[idx]

    def _endpoint_stats(self, records: list) -> dict:
        """Stats pour endpoint synchrone (POST /chat)."""
        latencies = [r.latency_ms for r in records if r.ok]
        errors = sum(1 for r in records if not r.ok)
        last = records[-1] if records else None
        return {
            "requests": len(records),
            "errors": errors,
            "p50_ms": self._percentile(latencies, 0.5),
            "p95_ms": self._percentile(latencies, 0.95),
            "last_latency_ms": last.latency_ms if last else None,
        }

    def _stream_stats(self, records: list) -> dict:
        """Stats pour endpoint SSE (GET /chat/stream)."""
        latencies = [r.latency_ms for r in records if r.ok]
        ttfts = [r.ttft_ms for r in records if r.ok and r.ttft_ms is not None]
        errors = sum(1 for r in records if not r.ok)
        last = records[-1] if records else None
        return {
            "requests": len(records),
            "errors": errors,
            "p50_ms": self._percentile(latencies, 0.5),
            "p95_ms": self._percentile(latencies, 0.95),
            "p50_ttft_ms": self._percentile(ttfts, 0.5),
            "p95_ttft_ms": self._percentile(ttfts, 0.95),
            "last_latency_ms": last.latency_ms if last else None,
            "last_ttft_ms": last.ttft_ms if last else None,
            "last_token_count": last.token_count if last else None,
            "last_tokens_per_sec": last.tokens_per_sec if last else None,
        }
