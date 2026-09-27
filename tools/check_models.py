"""Smoke test: verify all configured OpenRouter models answer."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engine.providers import get_provider  # noqa: E402


def main() -> int:
    reg = get_provider()
    print("provider:", reg.config.get("models", {}).get("provider"))
    print("registered:", list(reg.providers))
    failures = 0
    for stage in ("cheap", "medium", "expensive"):
        model = reg.get_model_for_stage(stage)
        try:
            resp = reg.complete("Reply with exactly: OK", stage=stage, max_tokens=16)
            text = resp.content.strip()[:40]
            tokens = resp.usage.get("completion_tokens", "?")
            print(f"[OK]   {stage:9s} {model:44s} -> {text!r} tokens={tokens} cached={resp.cached}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {stage:9s} {model:44s} -> {exc}")
    reg.close()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
