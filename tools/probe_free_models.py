"""Probe free OpenRouter models: check which answer reliably right now."""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engine.config import secret  # noqa: E402

CANDIDATES = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "poolside/laguna-s-2.1:free",
    "cohere/north-mini-code:free",
    "thinkingmachines/inkling:free",
    "nvidia/nemotron-3.5-lightning:free",
]


def probe(model: str, key: str) -> tuple[bool, str]:
    body = (
        '{"model":"%s","messages":[{"role":"user","content":"Reply with exactly: OK"}],'
        '"max_tokens":16}' % model
    ).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "DailyVibeEngine",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            import json
            data = json.loads(resp.read().decode())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return bool(content), content.strip()[:30]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:150]
        return False, f"HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:150]


def main() -> int:
    key = secret("OPENROUTER_API_KEY")
    if not key:
        print("No OPENROUTER_API_KEY")
        return 1
    working = []
    for model in CANDIDATES:
        ok, detail = probe(model, key)
        print(f"[{'OK' if ok else '--'}] {model:46s} {detail}")
        if ok:
            working.append(model)
    print("\nWorking:", working)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
