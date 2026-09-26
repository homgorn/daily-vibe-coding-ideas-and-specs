"""Tests for index module: multi-level MD indexes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.store.db import init_db
from engine.index import (
    build_global_index,
    build_day_index,
    build_cluster_index,
    build_tag_indexes,
    build_idea_indexes,
    build_all_indexes,
)


def setup_test_db(tmp_path):
    """Create a test DB with some data."""
    conn = init_db(tmp_path / "index_test.db")

    # Add source
    conn.execute("INSERT INTO sources (name, kind) VALUES ('github', 'github')")
    conn.execute("INSERT INTO sources (name, kind) VALUES ('hn', 'web')")

    # Add items
    for i in range(5):
        fp = f"test-fp-{i}"
        conn.execute(
            "INSERT INTO items (fingerprint, source_id, title, url, description) VALUES (?, 1, ?, ?, ?)",
            (fp, f"Test Repo {i}", f"https://github.com/test/{i}", f"Description {i}")
        )

    # Add mentions for today
    from datetime import date
    today = date.today().isoformat()
    for i in range(1, 6):
        conn.execute("INSERT INTO mentions (item_id, day) VALUES (?, ?)", (i, today))

    # Add clusters
    conn.execute("INSERT INTO clusters (name) VALUES ('AI Agents')")
    conn.execute("INSERT INTO clusters (name) VALUES ('LLM Tools')")
    for i in range(1, 4):
        conn.execute("INSERT INTO item_clusters (item_id, cluster_id) VALUES (?, 1)", (i,))
    for i in range(4, 6):
        conn.execute("INSERT INTO item_clusters (item_id, cluster_id) VALUES (?, 2)", (i,))

    # Add tags
    conn.execute("INSERT INTO tags (name) VALUES ('ai-agents')")
    conn.execute("INSERT INTO tags (name) VALUES ('mcp')")
    conn.execute("INSERT INTO tags (name) VALUES ('llm')")
    for tid in (1, 2):
        conn.execute("INSERT INTO item_tags (item_id, tag_id) VALUES (1, ?)", (tid,))
    conn.execute("INSERT INTO item_tags (item_id, tag_id) VALUES (2, 3)")
    conn.execute("INSERT INTO item_tags (item_id, tag_id) VALUES (3, 1)")

    # Add ideas
    import json
    viability = json.dumps({"market": 70, "competition": 50, "time_to_mvp": 60,
                            "risk": 40, "score": 68, "confidence": 75})
    conn.execute(
        "INSERT INTO ideas (title, summary, origin, status, viability) VALUES (?, ?, 'research', 'new', ?)",
        ("AI Code Review Bot", "Automated PR review with AI", viability)
    )
    conn.execute(
        "INSERT INTO ideas (title, summary, origin, status, viability) VALUES (?, ?, 'user', 'spec', ?)",
        ("MCP Server Manager", "Manage MCP servers easily", viability)
    )

    # Add specs
    conn.execute("INSERT INTO specs (idea_id, path, status) VALUES (1, 'data/specs/1_test.md', 'draft')")

    # Add related links
    conn.execute(
        "INSERT INTO related_links (from_id, to_id, relation, weight) VALUES (1, 2, 'cluster', 1.0)"
    )

    # Note: item_tags references items(id) — ideas get tags via separate mechanism
    # For test purposes, tags are on items already

    conn.commit()
    return conn


def test_build_global_index(tmp_path):
    conn = setup_test_db(tmp_path)
    path = build_global_index(conn)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "# Global Index" in content
    assert "AI Code Review Bot" in content
    assert "AI Agents" in content
    assert "ai-agents" in content


def test_build_day_index(tmp_path):
    from datetime import date
    conn = setup_test_db(tmp_path)
    today = date.today().isoformat()
    path = build_day_index(conn, today)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert f"# Day: {today}" in content
    assert "Test Repo" in content


def test_build_cluster_index(tmp_path):
    conn = setup_test_db(tmp_path)
    paths = build_cluster_index(conn)
    assert len(paths) == 2
    for p in paths:
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "# Cluster:" in content


def test_build_tag_indexes(tmp_path):
    conn = setup_test_db(tmp_path)
    paths = build_tag_indexes(conn)
    assert len(paths) == 3  # ai-agents, mcp, llm
    for p in paths:
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "# Tag:" in content


def test_build_idea_indexes(tmp_path):
    conn = setup_test_db(tmp_path)
    paths = build_idea_indexes(conn)
    assert len(paths) == 2
    for p in paths:
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "# Idea:" in content
        assert "← Global Index" in content


def test_idea_index_has_related(tmp_path):
    conn = setup_test_db(tmp_path)
    paths = build_idea_indexes(conn)
    # Idea 1 should have related link to Idea 2
    idea1_path = None
    for p in paths:
        if "idea_1" in p.name:
            idea1_path = p
            break
    assert idea1_path
    content = idea1_path.read_text(encoding="utf-8")
    assert "Related Ideas" in content
    assert "MCP Server Manager" in content


def test_build_all_indexes(tmp_path):
    conn = setup_test_db(tmp_path)
    results = build_all_indexes(conn)
    assert Path(results["global"]).exists()
    assert Path(results["publish"]).exists()
    assert len(results["days"]) >= 1
    assert len(results["clusters"]) == 2
    assert len(results["tags"]) == 3
    assert len(results["ideas"]) == 2


def test_publish_index(tmp_path):
    from engine.index import build_publish_index
    path = build_publish_index()
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Daily Vibe Coding Ideas and Specs" in content
    assert "## Latest Ideas" in content
    assert "## Specs" in content