"""Live check: does a real free model return parseable spec JSON?"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.spec as spec_mod  # noqa: E402
from engine.providers import get_provider  # noqa: E402

IDEA = {
    "id": 1,
    "title": "Repo Rater — ranks new GitHub repos by vibe-coding readiness",
    "summary": "Builders waste days on abandoned repos. Rater scores new repos.",
    "viability": {"score": 72, "confidence": 60},
    "tags": ["tools"],
    "status": "new",
    "origin": "research",
}
ITEMS = [
    {
        "title": "some/ai-agent-kit",
        "url": "https://github.com/some/ai-agent-kit",
        "description": "Toolkit for building LLM agents with MCP support.",
        "source_name": "github",
        "meta": '{"stars": 1200}',
    }
]


def main() -> int:
    reg = get_provider()
    reg.start_budget("spec")
    for model in reg.models_for_stage("spec"):
        print(f"--- trying {model}")
        try:
            resp = reg.complete(
                "Return ONLY a JSON object with a key \"problem\" whose value is a "
                "markdown heading followed by two sentences. No fences, no prose.",
                stage="expensive",
                max_tokens=300,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    call failed: {str(exc)[:120]}")
            continue
        parsed = spec_mod.extract_json_object(resp.content)
        print(f"    raw      : {resp.content[:160]!r}")
        print(f"    parsed   : {bool(parsed)} -> {list(parsed)[:4] if parsed else None}")
        if parsed:
            print("    OK: JSON path works with this model")
            reg.close()
            return 0
    reg.close()
    print("\nNo model returned parseable JSON.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
