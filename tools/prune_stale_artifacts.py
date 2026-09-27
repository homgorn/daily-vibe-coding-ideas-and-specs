"""One-off maintenance: drop duplicate and orphaned artifacts in publish/data mirrors.

Rules (deliberately conservative - never removes the only copy of an artifact):
  1. duplicate: several files share the same `{id}_` prefix in one directory -> keep the
     newest (by mtime), delete the rest;
  2. orphan: the file's `idea_id` is not present in the `ideas` table -> delete.

Slug rules changed twice (2026-09-25): old files keep their old names, they are not renamed
because DB rows and MD indexes may reference them by name.

Idempotent. Dry-run by default, pass --apply to delete.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCAN_DIRS = [
    ROOT / "publish" / "en" / "ideas",
    ROOT / "publish" / "en" / "specs",
    ROOT / "publish" / "en" / "rankings",
    ROOT / "publish" / "en" / "courses",
]
DATA_GLOBS = [ROOT / "data" / "*" / "notes", ROOT / "data" / "*" / "specs"]


def _idea_id(text: str) -> int | None:
    m = re.search(r"^idea_id:\s*(\d+)\s*$", text, re.M)
    return int(m.group(1)) if m else None


def _collect_dirs() -> list[Path]:
    dirs = [d for d in SCAN_DIRS if d.exists()]
    for pattern in DATA_GLOBS:
        dirs.extend(sorted(p for p in ROOT.glob(str(pattern.relative_to(ROOT))) if p.is_dir()))
    return dirs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(ROOT / "db" / "engine.db")
    known_ideas = {r[0] for r in conn.execute("SELECT id FROM ideas")}
    conn.close()

    plan: list[tuple[Path, str]] = []
    for d in _collect_dirs():
        groups: dict[str, list[Path]] = {}
        for p in sorted(d.glob("*.md")):
            idea_id = _idea_id(p.read_text(encoding="utf-8", errors="replace"))
            if idea_id is None:
                continue
            if idea_id not in known_ideas:
                plan.append((p, f"orphan: idea_id {idea_id} not in DB"))
                continue
            groups.setdefault(str(idea_id), []).append(p)
        for idea_id, files in groups.items():
            if len(files) < 2:
                continue
            keep = max(files, key=lambda f: f.stat().st_mtime)
            for f in files:
                if f != keep:
                    plan.append((f, f"duplicate of idea {idea_id} (kept {keep.name[:50]})"))

    print(f"to remove: {len(plan)}")
    for p, why in plan:
        print(f"  {p.relative_to(ROOT)}  <- {why}")

    if not args.apply:
        print("(dry run, use --apply)")
        return 0

    for p, _ in plan:
        p.unlink()
    print(f"removed: {len(plan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
