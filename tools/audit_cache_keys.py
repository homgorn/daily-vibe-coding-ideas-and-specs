"""Which keys did the model actually return per cached call?"""

from __future__ import annotations

import json
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
        "WHERE model LIKE 'nvidia/%' ORDER BY created_at DESC LIMIT 12"
    )
)

for created_at, raw in rows:
    parsed = extract_json_object(raw)
    keys = list(parsed) if parsed else None
    print(f"{created_at}  chars={len(raw):6d}  keys={keys}")
