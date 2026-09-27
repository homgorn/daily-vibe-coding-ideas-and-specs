"""Print ideas table (UTF-8 safe on Windows consoles)."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.store.db import init_db  # noqa: E402


def main() -> int:
    conn = init_db()
    for r in conn.execute("SELECT id, status, origin, title, summary FROM ideas ORDER BY id"):
        print(f"{r['id']:3d} | {r['status']:8s} | {r['origin']:8s} | {r['title'][:55]}")
        print(f"      {(r['summary'] or '')[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
