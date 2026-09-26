"""One-off maintenance: rename non-ASCII artifact filenames to ASCII and fix DB paths.

Idempotent: safe to re-run. Dry-run by default, pass --apply to perform renames.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.store import safe_name

ROOTS = [ROOT / "data", ROOT / "publish", ROOT / "index", ROOT / "research",
         ROOT / "knowledge", ROOT / "candidates", ROOT / "manual", ROOT / "ingest"]


def is_ascii(name: str) -> bool:
    return name.isascii()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    plan: list[tuple[Path, Path]] = []
    for base in ROOTS:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or is_ascii(p.name):
                continue
            if p.suffix.lower() not in (".md", ".json", ".txt", ".csv"):
                continue
            stem = p.stem
            new_stem = stem
            # rebuild the stem from its parts, ASCII-folding the title-ish tail
            parts = stem.split("_", 1)
            if len(parts) == 2:
                prefix, rest = parts
                new_stem = f"{prefix}_{safe_name(rest, max_len=60)}"
            else:
                new_stem = safe_name(stem, max_len=60)
            new_p = p.with_name(new_stem + p.suffix)
            plan.append((p, new_p))

    print(f"candidates: {len(plan)}")
    for old, new in plan:
        flag = "EXISTS" if new.exists() else "ok"
        print(f"  {old.relative_to(ROOT)}\n    -> {new.relative_to(ROOT)}  [{flag}]")

    if not args.apply:
        print("(dry run, use --apply)")
        return 0

    renamed = 0
    db_updates: list[tuple[str, str]] = []
    for old, new in plan:
        if new.exists() and new != old:
            print(f"SKIP (target exists): {new}")
            continue
        db_updates.append((str(old), str(new)))
        old.rename(new)
        renamed += 1

    conn = sqlite3.connect(ROOT / "db" / "engine.db")
    conn.row_factory = sqlite3.Row
    fixed = 0
    for old, new in db_updates:
        cur = conn.execute(
            "UPDATE specs SET path = ? WHERE path = ?", (new, old)
        )
        fixed += cur.rowcount
    conn.commit()
    rows = conn.execute("SELECT path FROM specs").fetchall()
    conn.close()
    print(f"renamed files: {renamed}, db rows updated: {fixed}")
    bad = [r["path"] for r in rows if not Path(r["path"]).name.isascii()]
    print("non-ascii spec paths left:", bad or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
