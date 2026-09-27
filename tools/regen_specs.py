"""Regenerate specs for all ideas in 'new' state (no spec row)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.config import load_config  # noqa: E402
from engine.providers import get_provider  # noqa: E402
from engine.spec import run_spec_generation  # noqa: E402


def main() -> int:
    cfg = load_config()
    registry = get_provider(cfg)
    registry.start_budget("spec")
    out = run_spec_generation(cfg)
    print(f"specs: {out.get('specs')}")
    if out.get("errors"):
        print(f"errors: {len(out['errors'])}")
        for err in out["errors"][:5]:
            print(f"  idea {err['idea_id']}: {err['error'][:140]}")
    if out.get("skipped_budget"):
        print("stopped early: LLM budget exhausted")
    print(f"llm minutes: {registry.budget_report()}")
    registry.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
