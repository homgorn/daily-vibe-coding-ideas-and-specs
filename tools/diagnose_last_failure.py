"""Was the last failure truncation, or a malformed payload?

Distinguishes them: truncation leaves an unclosed brace, a malformed payload
closes but does not parse. The fixes are different, so guessing wastes a
round-trip.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.spec import extract_json_object  # noqa: E402

conn = sqlite3.connect(ROOT / "db" / "llm_cache.sqlite")
rows = list(
    conn.execute(
        "SELECT created_at, response FROM llm_cache "
        "WHERE model LIKE 'nvidia/%' ORDER BY created_at DESC LIMIT 14"
    )
)

print(f"{'when':22s} {'chars':>6} {'closed':>7}  verdict / keys")
for created_at, raw in rows:
    closed = raw.rstrip().endswith("}")
    parsed = extract_json_object(raw)
    if not closed:
        verdict = "TRUNCATED (retryable by asking again)"
    elif parsed is None:
        verdict = "CLOSED BUT UNPARSEABLE (malformed payload, retry may not help)"
    else:
        verdict = f"ok  keys={list(parsed)}"
    print(f"{created_at:22s} {len(raw):6d} {str(closed):>7}  {verdict}")
