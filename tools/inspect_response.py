"""Inspect the raw shape of a spec response that fails to parse."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.config import secret  # noqa: E402
from engine.spec import extract_json_object  # noqa: E402

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

PROMPT = (
    "Generate a HYPER-DETAILED, AGENT-READY SPEC for this idea.\n\n"
    "## Idea\n"
    "**Title**: Repo Rater — ranks new GitHub repos by vibe-coding readiness\n"
    "**Summary**: Builders waste days on abandoned repos. Rater scores new repos.\n\n"
    "## Required Output Format\n"
    "Return ONLY a JSON object with these Markdown string fields:\n\n"
    + json.dumps({
        "problem": "## Problem\n\n...",
        "solution": "## Solution\n\n...",
        "target_user": "## Target User\n\n...",
        "cited_sources": "## Cited Sources\n\n[1] Title — URL",
    }, indent=2)
    + "\n\nBe concise. No prose outside the JSON."
)


def main() -> int:
    key = secret("OPENROUTER_API_KEY")
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 3000,
        "temperature": 0.5,
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
    content = choice.get("message", {}).get("content", "") or ""
    print("finish_reason:", choice.get("finish_reason"), flush=True)
    print("completion_tokens:", data.get("usage", {}).get("completion_tokens"), flush=True)
    print("chars:", len(content), flush=True)
    print("--- first 400 ---", flush=True)
    print(content[:400], flush=True)
    print("--- last 400 ---", flush=True)
    print(content[-400:], flush=True)
    print("--- shape ---", flush=True)
    print("starts with {:", content.lstrip().startswith("{"), flush=True)
    print("fence present:", "```" in content, flush=True)
    print("count of {:", content.count("{"), "count of }:", content.count("}"), flush=True)
    parsed = extract_json_object(content)
    print("parsed:", bool(parsed), flush=True)
    if parsed:
        print("keys:", list(parsed), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
