"""Report how many specs are real vs fell back to FALLBACK_MARKER."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.spec import FALLBACK_MARKER  # noqa: E402

REQUIRED = (
    "## Problem", "## Solution", "## Target User", "## Key Features",
    "## Tech Stack & Architecture", "## Data Model", "## API / Interfaces",
    "## UI/UX Requirements", "## Monetization", "## Risks & Mitigation",
    "## Launch Checklist", "## Cited Sources",
)


def main() -> int:
    specs = sorted((ROOT / "publish" / "en" / "specs").glob("*.md"))
    real = fallback = 0
    for path in specs:
        text = path.read_text(encoding="utf-8", errors="replace")
        is_fallback = FALLBACK_MARKER in text
        missing = [s for s in REQUIRED if s not in text]
        not_provided = text.count("(not provided by model)")
        if is_fallback:
            fallback += 1
            verdict = "FALLBACK (never generated)"
        elif missing or not_provided:
            fallback += 1
            verdict = f"PARTIAL: {len(missing)} sections missing, {not_provided} fields empty"
        else:
            real += 1
            verdict = "OK: all 12 sections present"
        print(f"{path.name[:58]:60s} {verdict}")
    print(f"\nreal={real}  incomplete={fallback}  total={len(specs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
