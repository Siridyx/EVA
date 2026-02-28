"""
EVA Engine Profiler — R-044

Profile le pipeline EVA complet (sans Ollama) avec mock LLM.
Fournit des chiffres CPU reproductibles sur les composants non-LLM.

Usage :
    python tools/profile_engine.py
    python tools/profile_engine.py --n 200 --top 30

Sorties :
    === Sous-timings moyens (N=100 appels) ===
    memory_message_added    :   2.4 ms / event (2 events/appel)
    llm_request_completed   :   0.1 ms (mock — LLM réel : 100-5000ms)
    conversation_turn_total :   5.2 ms (sans LLM)

    === Top 20 fonctions (cProfile, cumtime) ===
    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    ...
"""

from __future__ import annotations

import argparse
import cProfile
import io
import os
import pstats
import sys
import tempfile
import time
from collections import defaultdict
from typing import Any, Dict, List


# --- Mock LLM Transport (format Ollama) ---

class MockOllamaTransport:
    """Transport mock retournant une réponse Ollama fixe (pas de réseau)."""

    RESPONSE = "Je suis EVA, votre assistant IA personnel, conçu pour vous aider."

    def post(self, url: str, json: Any, headers: Any, timeout: Any) -> Dict[str, Any]:  # noqa: A002
        return {"response": self.RESPONSE}


# --- Setup EVA stack ---

def _setup_eva(tmp_dir: str):
    """Initialise le stack EVA complet avec mock LLM dans tmp_dir."""
    os.environ["EVA_DATA_DIR"] = tmp_dir

    from eva.core.config_manager import ConfigManager
    from eva.core.event_bus import EventBus
    from eva.core.eva_engine import EVAEngine
    from eva.conversation.conversation_engine import ConversationEngine
    from eva.llm.providers.ollama_provider import OllamaProvider
    from eva.memory.memory_manager import MemoryManager
    from eva.prompt.prompt_manager import PromptManager

    config = ConfigManager()
    bus = EventBus()

    memory = MemoryManager(config, bus)
    memory.start()

    prompt = PromptManager(config, bus)
    prompt.start()

    llm = OllamaProvider(config, bus, transport=MockOllamaTransport())
    llm.start()

    conv = ConversationEngine(config, bus, memory, prompt, llm)
    conv.start()

    engine = EVAEngine(config, bus)
    engine.set_conversation_engine(conv)
    engine.start()

    return engine, bus


# --- Event timing collector ---

def _install_timing_listener(bus) -> Dict[str, List[float]]:
    """Abonne des listeners au bus pour collecter les timings par event.

    EventBus.on() : handler(payload: dict) -> None  (pas d'event_name)
    → closures individuelles par event.
    """
    timings: Dict[str, List[float]] = defaultdict(list)
    _timestamps: Dict[str, float] = {}

    def on_turn_start(payload: Any) -> None:
        _timestamps["turn"] = time.perf_counter()

    def on_turn_complete(payload: Any) -> None:
        if "turn" in _timestamps:
            timings["conversation_turn_ms"].append(
                (time.perf_counter() - _timestamps.pop("turn")) * 1000
            )

    def on_llm_start(payload: Any) -> None:
        _timestamps["llm"] = time.perf_counter()

    def on_llm_complete(payload: Any) -> None:
        if "llm" in _timestamps:
            timings["llm_complete_ms"].append(
                (time.perf_counter() - _timestamps.pop("llm")) * 1000
            )

    def on_memory_add(payload: Any) -> None:
        timings["memory_add_count"].append(1.0)

    bus.on("conversation_turn_start",    on_turn_start)
    bus.on("conversation_turn_complete", on_turn_complete)
    bus.on("llm_request_started",        on_llm_start)
    bus.on("llm_request_completed",      on_llm_complete)
    bus.on("memory_message_added",       on_memory_add)

    return timings


def _avg(lst: List[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0


def run_profile(n: int = 100, top_n: int = 20) -> int:
    with tempfile.TemporaryDirectory(prefix="eva_profile_") as tmp_dir:
        print(f"\nEVA Engine Profiler — R-044")
        print(f"tmp_dir : {tmp_dir}")
        print(f"n_iterations : {n}  (mock LLM — pas d'Ollama)")
        print()

        # Setup
        print("Initialisation EVA (mock LLM)...", end=" ", flush=True)
        engine, bus = _setup_eva(tmp_dir)
        timings = _install_timing_listener(bus)
        print("OK")

        # Warm-up (5 appels)
        print("Warm-up (5 appels)...", end=" ", flush=True)
        for _ in range(5):
            engine.process("Bonjour EVA !")
        timings.clear()  # reset après warm-up
        print("OK")

        # Profiling cProfile
        print(f"Profiling cProfile ({n} appels)...", end=" ", flush=True)
        pr = cProfile.Profile()
        pr.enable()
        t_total_start = time.perf_counter()
        for _ in range(n):
            engine.process("Bonjour EVA !")
        t_total = (time.perf_counter() - t_total_start) * 1000
        pr.disable()
        print("OK")
        print()

        # --- Sous-timings par event ---
        print("=" * 60)
        print(f"Sous-timings moyens (N={n} appels, mock LLM)")
        print("=" * 60)

        turn_ms_list = timings.get("conversation_turn_ms", [])
        llm_ms_list = timings.get("llm_complete_ms", [])
        mem_count = sum(timings.get("memory_add_count", []))

        def print_timing(label: str, value_ms: float, note: str = "") -> None:
            note_str = f"  ({note})" if note else ""
            print(f"  {label:<35s} : {value_ms:7.3f} ms{note_str}")

        print_timing("Temps total / appel", t_total / n)
        print_timing("conversation_turn_complete", _avg(turn_ms_list),
                     f"n={len(turn_ms_list)}")
        print_timing("llm_complete (mock)", _avg(llm_ms_list),
                     "LLM réel = 100–5000ms")
        print_timing("memory saves total / appel",
                     (t_total / n) - _avg(turn_ms_list) if turn_ms_list else 0.0,
                     "estimé")
        print_timing("memory_add events total", mem_count,
                     "events (2/appel = user+assistant)")
        print()

        # --- Top N cProfile ---
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(top_n)
        profile_output = s.getvalue()

        print("=" * 60)
        print(f"Top {top_n} fonctions — cProfile (cumtime, {n} appels)")
        print("=" * 60)
        # Filtrer les lignes vides de tête
        lines = [l for l in profile_output.splitlines() if l.strip() or "function" in l.lower()]
        print("\n".join(lines))
        print()

        # --- Résumé ---
        print("=" * 60)
        print("Résumé")
        print("=" * 60)
        print(f"  Temps total     : {t_total:.1f} ms pour {n} appels")
        print(f"  Temps / appel   : {t_total / n:.3f} ms  (pipeline seul, LLM mocké)")
        print(f"  Throughput mock : {1000 * n / t_total:.1f} appels/sec")
        print()
        print("  NOTE : LLM Ollama reel = 100-5000ms dominant -> throughput reel ~0.2-10 appels/sec")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile le pipeline EVA avec mock LLM (sans Ollama).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=100, help="Nombre d'appels à profiler")
    parser.add_argument("--top", type=int, default=20, help="Top N fonctions cProfile")
    args = parser.parse_args()
    return run_profile(n=args.n, top_n=args.top)


if __name__ == "__main__":
    sys.exit(main())
