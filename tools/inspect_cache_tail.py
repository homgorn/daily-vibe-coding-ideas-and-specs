"""Show the tail of a cached response to confirm truncation."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

conn = sqlite3.connect(ROOT / "db" / "llm_cache.sqlite")
raw = list(
    conn.execute(
        "SELECT created_at, response FROM llm_cache "
        "WHERE model LIKE 'nvidia/%' ORDER BY created_at DESC LIMIT 12"
    )
)

for created_at, text in raw:
    if len(text) < 1500:
        continue
    print(f"=== {created_at}  chars={len(text)}")
    print("HEAD:", repr(text[:150]))
    print("TAIL:", repr(text[-220:]))
    print("ends_with_brace:", text.rstrip().endswith("}"))
    print()
