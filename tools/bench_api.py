"""
EVA API Bench — R-044

Benchmark black-box de l'API EVA.
Mesure les latences p50/p95/max pour /health, /status, /chat, /chat/stream.

Prérequis :
    eva --api          (terminal 1)
    Ollama running     (nécessaire pour /chat)

Usage :
    KEY=$(eva --print-api-key)
    python tools/bench_api.py --key "$KEY"
    python tools/bench_api.py --key "$KEY" --n-chat 10 --no-chat-stream
    python tools/bench_api.py --key "$KEY" --url http://127.0.0.1:8000

Sortie :
    ============================================================
    EVA API Bench  http://127.0.0.1:8000
    warm-up=3  n_health=30  n_status=30  n_chat=20
    ============================================================
    GET /health           p50=   4.2ms  p95=   7.1ms  max=  11.3ms  (n=30)
    GET /status           p50=   5.8ms  p95=   8.4ms  max=  12.1ms  (n=30)
    POST /chat            p50=1842.3ms  p95=3210.5ms  max=4821.0ms  (n=20)
    GET /chat/stream TTFT p50=1856.1ms  p95=3218.0ms  max=4830.0ms  (n=20)
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from typing import List


def _percentile(data: List[float], pct: float) -> float:
    """Percentile Nth d'une liste triée."""
    sorted_data = sorted(data)
    idx = max(0, int(len(sorted_data) * pct / 100) - 1)
    return sorted_data[idx]


def _print_stats(label: str, ms: List[float]) -> None:
    p50 = statistics.median(ms)
    p95 = _percentile(ms, 95)
    print(f"{label:<30s}  p50={p50:8.1f}ms  p95={p95:8.1f}ms  max={max(ms):8.1f}ms  (n={len(ms)})")


def run_bench(
    base_url: str,
    api_key: str,
    warmup: int = 3,
    n_health: int = 30,
    n_status: int = 30,
    n_chat: int = 20,
    n_stream: int = 10,
    skip_chat: bool = False,
    skip_stream: bool = True,
    message: str = "Bonjour, qui es-tu en une phrase ?",
) -> int:
    try:
        import requests
    except ImportError:
        print("Erreur : 'requests' non installé. pip install requests")
        return 1

    headers = {"Authorization": f"Bearer {api_key}"}
    session = requests.Session()

    print(f"\n{'='*60}")
    print(f"EVA API Bench  {base_url}")
    print(f"warm-up={warmup}  n_health={n_health}  n_status={n_status}  n_chat={n_chat}")
    print("=" * 60)

    # --- Warm-up ---
    print(f"Warm-up ({warmup} requêtes)...", end=" ", flush=True)
    for _ in range(warmup):
        try:
            session.get(f"{base_url}/health", timeout=5)
            session.get(f"{base_url}/status", headers=headers, timeout=5)
        except Exception:
            pass
    print("OK")

    # --- GET /health ---
    health_ms: List[float] = []
    for _ in range(n_health):
        t0 = time.perf_counter()
        r = session.get(f"{base_url}/health", timeout=10)
        health_ms.append((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            print(f"WARN /health : HTTP {r.status_code}")
    _print_stats("GET /health", health_ms)

    # --- GET /status ---
    status_ms: List[float] = []
    for _ in range(n_status):
        t0 = time.perf_counter()
        r = session.get(f"{base_url}/status", headers=headers, timeout=10)
        status_ms.append((time.perf_counter() - t0) * 1000)
        if r.status_code not in (200, 503):
            print(f"WARN /status : HTTP {r.status_code}")
    _print_stats("GET /status", status_ms)

    # --- POST /chat ---
    if not skip_chat:
        chat_ms: List[float] = []
        for i in range(n_chat):
            t0 = time.perf_counter()
            r = session.post(
                f"{base_url}/chat",
                headers=headers,
                json={"message": message},
                timeout=120,
            )
            chat_ms.append((time.perf_counter() - t0) * 1000)
            if r.status_code not in (200, 503):
                print(f"WARN /chat [{i+1}] : HTTP {r.status_code}")
                if r.status_code == 503:
                    print("  (moteur EVA non démarré — Ollama requis)")
                    break
        if chat_ms:
            _print_stats("POST /chat", chat_ms)

    # --- GET /chat/stream (TTFT) ---
    if not skip_stream:
        ttft_ms: List[float] = []
        for i in range(n_stream):
            params = {"message": message, "api_key": api_key}
            t0 = time.perf_counter()
            try:
                with session.get(
                    f"{base_url}/chat/stream",
                    params=params,
                    stream=True,
                    timeout=120,
                ) as resp:
                    if resp.status_code != 200:
                        print(f"WARN /chat/stream [{i+1}] : HTTP {resp.status_code}")
                        break
                    first_token = False
                    for line in resp.iter_lines():
                        if line and line.startswith(b"event: token"):
                            if not first_token:
                                ttft_ms.append((time.perf_counter() - t0) * 1000)
                                first_token = True
                        if line and line.startswith(b"event: done"):
                            break
            except Exception as e:
                print(f"WARN /chat/stream [{i+1}] : {e}")
                break
        if ttft_ms:
            _print_stats("GET /chat/stream TTFT", ttft_ms)

    session.close()
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark black-box de l'API EVA.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL de base")
    parser.add_argument("--key", required=True, help="Clé API EVA")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--n-health", type=int, default=30)
    parser.add_argument("--n-status", type=int, default=30)
    parser.add_argument("--n-chat", type=int, default=20)
    parser.add_argument("--n-stream", type=int, default=10)
    parser.add_argument("--skip-chat", action="store_true", help="Passer /chat (sans Ollama)")
    parser.add_argument("--with-stream", action="store_true", help="Inclure /chat/stream")
    parser.add_argument("--message", default="Bonjour, qui es-tu en une phrase ?")
    args = parser.parse_args()

    return run_bench(
        base_url=args.url,
        api_key=args.key,
        warmup=args.warmup,
        n_health=args.n_health,
        n_status=args.n_status,
        n_chat=args.n_chat,
        n_stream=args.n_stream,
        skip_chat=args.skip_chat,
        skip_stream=not args.with_stream,
        message=args.message,
    )


if __name__ == "__main__":
    sys.exit(main())
