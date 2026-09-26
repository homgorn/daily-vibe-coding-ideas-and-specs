"""Dashboard data.json generation: no local absolute paths may leak into public output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.store.db as db_mod
import engine.store as store_mod
from engine.store.db import init_db


def _seed(conn, base: Path) -> None:
    conn.execute(
        "INSERT INTO ideas (title, summary, origin, status, viability, created_at)"
        " VALUES (?, ?, 'research', 'new', ?, '2026-09-25 10:00:00')",
        ("Idea with spec", "summary", json.dumps({"score": 71})),
    )
    idea_id = conn.execute("SELECT id FROM ideas ORDER BY id DESC LIMIT 1").fetchone()["id"]
    conn.execute(
        "INSERT INTO specs (idea_id, path, status, created_at)"
        " VALUES (?, ?, 'published', '2026-09-25 10:05:00')",
        (idea_id, str(base / "data" / "2026-09-25" / "specs" / "1_Idea_with_spec.md")),
    )
    conn.commit()


def test_dashboard_has_no_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "engine.db")
    monkeypatch.setattr(store_mod, "DATA_DIR", tmp_path / "data")
    conn = init_db()
    _seed(conn, tmp_path)

    import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.cmd_dashboard(argparse.Namespace()) == 0

    out = tmp_path / "dashboard" / "data.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    paths = [s["path"] for s in data["recent_specs"]]
    assert paths == ["data/2026-09-25/specs/1_Idea_with_spec.md"]

    raw = out.read_text(encoding="utf-8")
    assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]", raw), raw
    assert "recent_ideas" in data and data["recent_ideas"][0]["score"] == 71


def test_rel_path_outside_root(tmp_path):
    sys.path.insert(0, str(ROOT / "src"))
    import cli

    assert cli._rel_path("") == ""
    assert cli._rel_path(None) == ""
    assert cli._rel_path(str(tmp_path / "x" / "y.md")) == "y.md"
    assert cli._rel_path(str(ROOT / "publish" / "en" / "a.md")) == "publish/en/a.md"
