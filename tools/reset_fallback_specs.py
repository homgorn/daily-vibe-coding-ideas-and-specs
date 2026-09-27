"""Delete spec files the model never finished, so the next run regenerates them.

Uses `engine.spec.spec_is_incomplete` — the same definition the pipeline applies
when selecting ideas. A tool that disagrees with the pipeline about what
"incomplete" means is worse than no tool: it reports clean while the pipeline
keeps skipping.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.spec import spec_is_incomplete  # noqa: E402
from engine.store.db import init_db  # noqa: E402

# Fillers emitted by the pre-2026-09-27 silent fallback, before specs carried a
# visible marker. They read like a real spec, so they must be swept too.
LEGACY_FILLERS = (
    "See summary above.",
    "Generated from fetched items.",
    "1. Core feature (P0)",
)


def main() -> int:
    conn = init_db()
    rows = conn.execute("SELECT id, idea_id, path FROM specs").fetchall()
    removed = 0
    for row in rows:
        path = Path(row["path"])
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        stale = spec_is_incomplete(path) or any(f in text for f in LEGACY_FILLERS)
        if stale:
            conn.execute("DELETE FROM specs WHERE id = ?", (row["id"],))
            conn.execute(
                "UPDATE ideas SET status = 'new' WHERE id = ?", (row["idea_id"],)
            )
            path.unlink(missing_ok=True)
            removed += 1
            print(f"removed incomplete spec for idea {row['idea_id']}: {path.name}")
    conn.commit()
    print(f"total removed: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
