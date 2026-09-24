"""Карточки сервисов: frontmatter, индексация в БД, FTS-поиск, idempotent."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.knowledge import (  # noqa: E402
    SERVICES_DIR,
    index_service_docs,
    list_services,
    parse_frontmatter,
    search_services,
)
from engine.store.db import init_db  # noqa: E402


def test_parse_frontmatter():
    text = "---\nname: github\nkind: api\n---\n\nТело"
    meta, body = parse_frontmatter(text)
    assert meta["name"] == "github"
    assert meta["kind"] == "api"
    assert "Тело" in body


def test_parse_frontmatter_without_meta():
    meta, body = parse_frontmatter("просто текст")
    assert meta == {}
    assert body == "просто текст"


def test_github_card_present(tmp_path):
    assert (SERVICES_DIR / "github.md").exists()
    meta, _ = parse_frontmatter((SERVICES_DIR / "github.md").read_text(encoding="utf-8"))
    assert meta["name"] == "github"
    assert meta["kind"] == "api"
    assert meta["docs_url"]


def test_index_and_search(tmp_path):
    conn = init_db(tmp_path / "svc.db")
    names = index_service_docs(conn)
    assert "github" in names

    assert any(s["name"] == "github" for s in list_services(conn))

    found = search_services("github", conn)
    assert found and found[0]["name"] == "github"
    found = search_services("open", conn)
    assert found, "tags/endpoints/notes должны участвовать в FTS-поиске"
    found = search_services("trending OR repos", conn)
    assert found


def test_index_idempotent(tmp_path):
    conn = init_db(tmp_path / "svc2.db")
    index_service_docs(conn)
    index_service_docs(conn)
    n = conn.execute("SELECT COUNT(*) AS c FROM service_docs").fetchone()["c"]
    assert n == len(list_services(conn))
    assert n >= 1