"""Remove ideas that were manufactured from placeholder text, not from real input.

Targets only rows whose title/summary reproduce the inbox template's own
example line. Anything else is left alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.store.db import init_db  # noqa: E402

PLACEHOLDER_TITLES = {"Ссылки и идеи", "Links and ideas"}
PLACEHOLDER_SUMMARY_PARTS = ("добавь первую запись", "foo/bar")


def main() -> int:
    conn = init_db()
    removed: list[int] = []
    for row in conn.execute("SELECT id, title, summary FROM ideas").fetchall():
        title = (row["title"] or "").strip()
        summary = row["summary"] or ""
        is_placeholder = title in PLACEHOLDER_TITLES or any(
            part in summary for part in PLACEHOLDER_SUMMARY_PARTS
        )
        if not is_placeholder:
            continue
        idea_id = row["id"]
        for spec in conn.execute("SELECT path FROM specs WHERE idea_id = ?", (idea_id,)):
            Path(spec["path"]).unlink(missing_ok=True)
        conn.execute("DELETE FROM specs WHERE idea_id = ?", (idea_id,))
        conn.execute("DELETE FROM content_bundles WHERE idea_id = ?", (idea_id,))
        conn.execute("DELETE FROM item_tags WHERE item_id = ?", (idea_id,))
        conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
        removed.append(idea_id)
        print(f"removed placeholder idea {idea_id}: {title!r}")
    conn.commit()

    stale = 0
    for folder in ("publish/en/ideas", "publish/en/specs", "data"):
        for path in (ROOT / folder).rglob("*.md"):
            if "untitled" in path.name.lower() and any(
                part in path.read_text(encoding="utf-8", errors="replace")
                for part in PLACEHOLDER_SUMMARY_PARTS
            ):
                path.unlink(missing_ok=True)
                stale += 1
                print(f"removed stale artifact: {path.relative_to(ROOT)}")
    print(f"ideas removed: {removed}; stale artifacts removed: {stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
