"""Tests for ingest module: inbox parsing, candidates, manual ideas."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.ingest import (
    parse_inbox,
    parse_candidates,
    parse_manual_ideas,
    process_inbox,
    IngestItem,
)


def test_parse_inbox_nonexistent():
    """No inbox file → empty list."""
    import engine.ingest as ingest_mod
    original = ingest_mod.INBOX_PATH
    ingest_mod.INBOX_PATH = Path("/nonexistent/inbox.md")
    try:
        items = parse_inbox()
        assert items == []
    finally:
        ingest_mod.INBOX_PATH = original


def test_parse_inbox_with_content(tmp_path):
    """Parse inbox with structured entries."""
    import engine.ingest as ingest_mod
    inbox = tmp_path / "inbox.md"
    inbox.write_text("""# Inbox

## AI Code Review Tool
URL: https://github.com/example/ai-review
description: Automated code review using LLMs
tags: ai-agents, code-review

## MCP Server Discovery
https://github.com/example/mcp-discovery
""", encoding="utf-8")

    original = ingest_mod.INBOX_PATH
    ingest_mod.INBOX_PATH = inbox
    try:
        items = parse_inbox()
        assert len(items) == 2
        assert items[0].title == "AI Code Review Tool"
        assert items[0].url == "https://github.com/example/ai-review"
        assert items[0].tags == ["ai-agents", "code-review"]
        assert items[1].title == "MCP Server Discovery"
        assert items[1].url == "https://github.com/example/mcp-discovery"
    finally:
        ingest_mod.INBOX_PATH = original


def test_parse_candidates_nonexistent():
    import engine.ingest as ingest_mod
    original = ingest_mod.CANDIDATES_DIR
    ingest_mod.CANDIDATES_DIR = Path("/nonexistent/candidates")
    try:
        items = parse_candidates()
        assert items == []
    finally:
        ingest_mod.CANDIDATES_DIR = original


def test_parse_candidates_with_files(tmp_path):
    import engine.ingest as ingest_mod
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    (cand_dir / "ai-agent-ide.md").write_text(
        "---\ntitle: \"AI Agent IDE\"\ntags: [ai-agents, ide]\n---\n\nAn AI-powered IDE.\nhttps://github.com/example/ai-ide\n",
        encoding="utf-8"
    )

    original = ingest_mod.CANDIDATES_DIR
    ingest_mod.CANDIDATES_DIR = cand_dir
    try:
        items = parse_candidates()
        assert len(items) == 1
        assert items[0].title == "Ai Agent Ide"
        assert items[0].url == "https://github.com/example/ai-ide"
        assert "ai-agents" in items[0].tags
    finally:
        ingest_mod.CANDIDATES_DIR = original


def test_parse_manual_ideas_nonexistent():
    import engine.ingest as ingest_mod
    original = ingest_mod.MANUAL_DIR
    ingest_mod.MANUAL_DIR = Path("/nonexistent/manual")
    try:
        items = parse_manual_ideas()
        assert items == []
    finally:
        ingest_mod.MANUAL_DIR = original


def test_parse_manual_ideas_with_files(tmp_path):
    import engine.ingest as ingest_mod
    man_dir = tmp_path / "manual"
    man_dir.mkdir()
    (man_dir / "my-idea.md").write_text(
        "---\ntitle: \"My Great Idea\"\ntags: [saas, b2b]\n---\n\nA B2B SaaS product.\n",
        encoding="utf-8"
    )

    original = ingest_mod.MANUAL_DIR
    ingest_mod.MANUAL_DIR = man_dir
    try:
        items = parse_manual_ideas()
        assert len(items) == 1
        assert items[0].title == "My Great Idea"
        assert "saas" in items[0].tags
    finally:
        ingest_mod.MANUAL_DIR = original


def test_process_inbox_empty(tmp_path):
    """process_inbox with no sources returns zeros."""
    import engine.ingest as ingest_mod
    orig_inbox = ingest_mod.INBOX_PATH
    orig_cand = ingest_mod.CANDIDATES_DIR
    orig_man = ingest_mod.MANUAL_DIR
    ingest_mod.INBOX_PATH = tmp_path / "inbox.md"
    ingest_mod.CANDIDATES_DIR = tmp_path / "candidates"
    ingest_mod.MANUAL_DIR = tmp_path / "manual"
    try:
        stats = process_inbox(None)
        assert stats["total"] == 0
        assert stats["new"] == 0
    finally:
        ingest_mod.INBOX_PATH = orig_inbox
        ingest_mod.CANDIDATES_DIR = orig_cand
        ingest_mod.MANUAL_DIR = orig_man


def test_process_inbox_with_db(tmp_path):
    """process_inbox stores items in DB."""
    import engine.ingest as ingest_mod
    from engine.store.db import init_db

    # Setup inbox
    inbox = tmp_path / "inbox.md"
    inbox.write_text("## Test Idea\nURL: https://example.com/idea\n", encoding="utf-8")

    # Setup empty dirs
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    man_dir = tmp_path / "manual"
    man_dir.mkdir()

    orig_inbox = ingest_mod.INBOX_PATH
    orig_cand = ingest_mod.CANDIDATES_DIR
    orig_man = ingest_mod.MANUAL_DIR
    ingest_mod.INBOX_PATH = inbox
    ingest_mod.CANDIDATES_DIR = cand_dir
    ingest_mod.MANUAL_DIR = man_dir

    try:
        conn = init_db(tmp_path / "ingest.db")
        stats = process_inbox(conn)
        assert stats["inbox"] == 1
        assert stats["total"] == 1
        assert stats["new"] == 1

        # Verify in DB
        row = conn.execute("SELECT COUNT(*) as c FROM items").fetchone()
        assert row["c"] == 1
    finally:
        ingest_mod.INBOX_PATH = orig_inbox
        ingest_mod.CANDIDATES_DIR = orig_cand
        ingest_mod.MANUAL_DIR = orig_man


def test_ingest_item_dataclass():
    item = IngestItem(
        title="Test",
        url="https://example.com",
        description="A test",
        origin="user",
        tags=["a", "b"],
    )
    assert item.title == "Test"
    assert item.origin == "user"
    assert item.tags == ["a", "b"]