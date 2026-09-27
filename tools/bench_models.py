"""Benchmark free OpenRouter models: latency + tokens/sec on a spec-sized prompt."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engine.config import secret  # noqa: E402
from engine.providers import OpenRouterProvider  # noqa: E402

PROMPT = (
    "Write a technical spec section 'Solution' (about 350 words) for a CLI tool that "
    "fetches daily GitHub trending repos and summarizes them. Plain prose, no lists."
)

MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]


def main() -> int:
    key = secret("OPENROUTER_API_KEY")
    if not key:
        print("no OPENROUTER_API_KEY")
        return 1
    provider = OpenRouterProvider(key)
    for model in MODELS:
        started = time.monotonic()
        try:
            resp = provider.complete(PROMPT, model, max_tokens=700, temperature=0.4, retries=1)
            elapsed = time.monotonic() - started
            out_tokens = resp.usage.get("completion_tokens") or 0
            tps = out_tokens / elapsed if elapsed else 0
            print(
                f"{model:44s} {elapsed:6.1f}s  out={out_tokens:5d}  {tps:5.1f} tok/s  "
                f"chars={len(resp.content)}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"{model:44s} FAILED after {time.monotonic() - started:6.1f}s  {str(exc)[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
