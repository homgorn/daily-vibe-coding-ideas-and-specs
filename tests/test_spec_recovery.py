"""A partial spec must be recoverable, not permanent.

`run_spec_generation` used to select only ideas with no `specs` row, so a spec
that came back with four sections missing was never retried: the row existed,
the idea left the eligible statuses, and the artifact stayed broken forever.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.spec as spec_mod  # noqa: E402


def write_spec(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(
        f"---\ntitle: t\n---\n\n{body}\n\n## Launch Commands\n", encoding="utf-8"
    )
    return path


# --- the shared completeness definition ------------------------------------


def test_missing_file_counts_as_incomplete(tmp_path):
    assert spec_mod.spec_is_incomplete(tmp_path / "nope.md") is True


def test_fallback_spec_counts_as_incomplete(tmp_path):
    path = write_spec(tmp_path, "a.md", spec_mod.FALLBACK_MARKER)
    assert spec_mod.spec_is_incomplete(path) is True


def test_partial_spec_counts_as_incomplete(tmp_path):
    body = "## Problem\n\nok\n\n" + spec_mod.INCOMPLETE_MARKER + "\n\n## Solution\n\nx"
    path = write_spec(tmp_path, "b.md", body)
    assert spec_mod.spec_is_incomplete(path) is True


def test_complete_spec_counts_as_complete(tmp_path):
    body = "\n\n".join(f"## {key}\n\ntext" for key, _ in spec_mod.SPEC_SECTIONS)
    path = write_spec(tmp_path, "c.md", body)
    assert spec_mod.spec_is_incomplete(path) is False


# --- selection -------------------------------------------------------------


def _seed(conn, tmp_path, *, idea_id: int, status: str, body: str | None):
    conn.execute(
        "INSERT OR IGNORE INTO ideas (id, title, summary, status, origin) "
        "VALUES (?, 'T', 's', ?, 'research')",
        (idea_id, status),
    )
    if body is not None:
        path = write_spec(tmp_path, f"{idea_id}.md", body)
        conn.execute(
            "INSERT INTO specs (idea_id, path, status, created_at) "
            "VALUES (?, ?, 'draft', datetime('now'))",
            (idea_id, str(path)),
        )


def _selected_ids(tmp_path, rows) -> list[int]:
    conn = spec_mod.init_db(tmp_path / "select.db")
    try:
        for idea_id, status, body in rows:
            _seed(conn, tmp_path, idea_id=idea_id, status=status, body=body)
        return sorted(spec_mod.select_ideas_needing_specs(conn))
    finally:
        conn.close()


def test_idea_with_complete_spec_is_not_selected(tmp_path):
    complete = "\n\n".join(f"## {k}\n\ntext" for k, _ in spec_mod.SPEC_SECTIONS)
    assert _selected_ids(tmp_path, [(1, "spec", complete)]) == []


def test_idea_with_partial_spec_is_selected(tmp_path):
    partial = "## Problem\n\nok\n\n" + spec_mod.INCOMPLETE_MARKER
    assert _selected_ids(tmp_path, [(2, "spec", partial)]) == [2]


def test_idea_with_fallback_spec_is_selected(tmp_path):
    assert _selected_ids(tmp_path, [(3, "spec", spec_mod.FALLBACK_MARKER)]) == [3]


def test_idea_without_spec_row_is_selected(tmp_path):
    assert _selected_ids(tmp_path, [(4, "new", None)]) == [4]


def test_idea_with_spec_row_missing_from_disk_is_selected(tmp_path):
    conn = spec_mod.init_db(tmp_path / "gone.db")
    try:
        _seed(conn, tmp_path, idea_id=5, status="spec", body="x")
        conn.execute("UPDATE specs SET path = ? WHERE idea_id = 5", (str(tmp_path / "gone.md"),))
        assert spec_mod.select_ideas_needing_specs(conn) == [5]
    finally:
        conn.close()


# --- regeneration must not duplicate rows ----------------------------------


def test_regenerating_does_not_duplicate_the_specs_row(tmp_path):
    conn = spec_mod.init_db(tmp_path / "dup.db")
    try:
        conn.execute(
            "INSERT INTO ideas (id, title, summary, status, origin) "
            "VALUES (90, 'T', 's', 'new', 'research')"
        )
        spec_mod.save_spec(conn, 90, str(tmp_path / "90.md"))
        spec_mod.save_spec(conn, 90, str(tmp_path / "90-v2.md"))
        count = conn.execute(
            "SELECT COUNT(*) FROM specs WHERE idea_id = 90"
        ).fetchone()[0]
        assert count == 1, f"regeneration created {count} rows for one idea"
        path = conn.execute(
            "SELECT path FROM specs WHERE idea_id = 90"
        ).fetchone()[0]
        assert path.endswith("90-v2.md"), "the newest write must win"
    finally:
        conn.close()


def test_save_spec_is_idempotent_under_retry(tmp_path):
    """A failing idea that is retried must not accumulate spec rows."""
    conn = spec_mod.init_db(tmp_path / "retry.db")
    try:
        conn.execute(
            "INSERT INTO ideas (id, title, summary, status, origin) "
            "VALUES (91, 'T', 's', 'new', 'research')"
        )
        for _ in range(3):
            spec_mod.save_spec(conn, 91, "spec.md")
        assert conn.execute(
            "SELECT COUNT(*) FROM specs WHERE idea_id = 91"
        ).fetchone()[0] == 1
    finally:
        conn.close()
