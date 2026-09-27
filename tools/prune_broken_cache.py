"""Drop unusable entries from the LLM cache.

A response that never closed its JSON is worthless: it cannot be parsed, and
serving it again on an identical prompt blocks recovery forever. Measured
2026-09-27: 30 of 85 cached OpenRouter responses were truncated.

Spec generation now passes `cache=False` (ADR-009), so it no longer replays
these, but other stages share the same table.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / "db" / "llm_cache.sqlite"
    if not path.exists():
        print(f"no cache at {path}")
        return 1

    conn = sqlite3.connect(path)
    before = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    rows = conn.execute("SELECT key_hash, response FROM llm_cache").fetchall()
    doomed = [
        key for key, response in rows if not str(response).rstrip().endswith("}")
    ]
    conn.executemany("DELETE FROM llm_cache WHERE key_hash = ?", [(k,) for k in doomed])
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    conn.close()

    print(f"cache entries: {before} -> {after} (removed {len(doomed)} unclosed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
