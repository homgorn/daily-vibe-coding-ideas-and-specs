"""Decisive: is the spec JSON truncated at a given max_tokens?

Prints finish_reason so truncation is observed, not inferred.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.config import secret  # noqa: E402
from engine.spec import extract_json_object  # noqa: E402

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SECTIONS = {
    "problem": "## Problem\n\nDetailed problem statement",
    "solution": "## Solution\n\nExact solution",
    "target_user": "## Target User\n\nPrimary persona",
    "features": "## Key Features\n\n1. **Feature** — description (P0)",
    "tech_stack": "## Tech Stack & Architecture\n\nRecommended stack",
    "data_model": "## Data Model\n\nCore entities",
    "api": "## API / Interfaces\n\nKey endpoints",
    "ui_ux": "## UI/UX Requirements\n\nKey screens",
    "monetization": "## Monetization\n\nPricing model",
    "risks": "## Risks & Mitigation\n\n| Risk | Likelihood | Impact | Mitigation |",
    "launch_checklist": "## Launch Checklist\n\n1. [ ] Pre-launch",
    "cited_sources": "## Cited Sources\n\n[1] Title — URL",
}

PROMPT = (
    "Generate a HYPER-DETAILED, AGENT-READY SPEC for this idea.\n\n"
    "## Idea\n"
    "**Title**: Repo Rater — ranks new GitHub repos by vibe-coding readiness\n"
    "**Summary**: Builders waste days on abandoned repos. Rater scores new repos.\n"
    "**Tags**: tools\n\n"
    "## Source Materials (cite as [source:N])\n"
    + json.dumps(
        [{
            "title": "some/ai-agent-kit",
            "url": "https://github.com/some/ai-agent-kit",
            "description": "Toolkit for building LLM agents with MCP support.",
        }],
        indent=2,
    )
    + "\n\n## Required Output Format\n"
    "Return ONLY a JSON object with these Markdown string fields:\n\n"
    + json.dumps(SECTIONS, indent=2)
    + "\n\nStyle: Spec Kit constitution structure + BMAD role depth. "
    "Every claim from sources → [source:N]. No fluff. MVP scope 2-4 weeks."
)


def probe(max_tokens: int, key: str) -> None:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "DailyVibeEngine",
        },
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    choice = data["choices"][0]
    finish = choice.get("finish_reason")
    content = choice.get("message", {}).get("content", "") or ""
    usage = data.get("usage", {})
    parsed = extract_json_object(content)
    print(
        f"max_tokens={max_tokens:5d}  finish_reason={finish:8s}  "
        f"completion={usage.get('completion_tokens')}  chars={len(content)}  "
        f"parsed={bool(parsed)}"
        + (f"  keys={len(parsed)}" if parsed else ""),
        flush=True,
    )


def main() -> int:
    key = secret("OPENROUTER_API_KEY")
    for cap in (2000, 6000):
        try:
            probe(cap, key)
        except urllib.error.HTTPError as exc:
            print(f"max_tokens={cap:5d}  HTTP {exc.code}: {exc.read().decode()[:150]}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"max_tokens={cap:5d}  FAILED {str(exc)[:150]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
