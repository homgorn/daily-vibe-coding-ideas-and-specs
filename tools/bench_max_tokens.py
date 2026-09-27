"""Measure how max_tokens affects latency and actual output length.

max_tokens is a *cap*, not a target. This measures whether raising the cap
slows a request down even when the model stops early on its own.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engine.config import secret  # noqa: E402
from engine.providers import OpenRouterProvider  # noqa: E402

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

PROMPTS = {
    "short": "In one sentence, what is a treemap?",
    "medium": "Explain how git rebase works, about 150 words. Plain prose.",
    "long": "Write a technical spec section 'Solution' (about 350 words) for a "
            "CLI that fetches daily GitHub trending repos and summarizes them. "
            "Plain prose, no lists.",
}

CAPS = [256, 1024, 2000, 4096, 8192]
REPEATS = 2


def run(provider: OpenRouterProvider, prompt: str, cap: int) -> tuple[float, int, str]:
    started = time.monotonic()
    try:
        resp = provider.complete(prompt, MODEL, max_tokens=cap, temperature=0.4, retries=4)
    except Exception as exc:  # noqa: BLE001
        return time.monotonic() - started, 0, f"ERR {str(exc)[:200]}"
    elapsed = time.monotonic() - started
    out = resp.usage.get("completion_tokens")
    if out is None:
        out = max(1, len(resp.content) // 4)
    return elapsed, out, ""


def main() -> int:
    key = secret("OPENROUTER_API_KEY")
    if not key:
        print("no OPENROUTER_API_KEY")
        return 1
    provider = OpenRouterProvider(key)

    for label, prompt in PROMPTS.items():
        print(f"\n=== prompt: {label} ===")
        print(f"{'cap':>6} {'median s':>9} {'out tok':>8} {'tok/s':>7}")
        for cap in CAPS:
            times, outs = [], []
            for _ in range(REPEATS):
                elapsed, out, err = run(provider, prompt, cap)
                if err:
                    print(f"{cap:>6} {'-':>9} {'-':>8}  {err}")
                    break
                times.append(elapsed)
                outs.append(out)
            if not times:
                continue
            med = statistics.median(times)
            avg_out = statistics.mean(outs)
            print(f"{cap:>6} {med:>9.1f} {avg_out:>8.0f} {avg_out / med if med else 0:>7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
