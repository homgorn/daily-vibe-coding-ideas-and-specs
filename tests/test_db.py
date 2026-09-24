"""Миграции и работа БД: применение, идемпотентность, ключевые таблицы."""

from __future__ import annotations

import sqlite3

from engine.store.db import MIGRATIONS, get_conn, init_db, migrate


def test_migrations_apply_and_idempotent(tmp_path):
    db = tmp_path / "test.db"
    conn = init_db(db)
    applied = conn.execute("SELECT COUNT(*) AS c FROM schema_migrations").fetchone()["c"]
    assert applied == len(MIGRATIONS)

    migrate(conn)  # повторный прогон — без ошибок и без дублей
    applied2 = conn.execute("SELECT COUNT(*) AS c FROM schema_migrations").fetchone()["c"]
    assert applied2 == len(MIGRATIONS)


def test_required_tables_exist(tmp_path):
    conn = init_db(tmp_path / "t.db")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    for t in [
        "schema_migrations", "sources", "items", "mentions", "news_items",
        "clusters", "item_clusters", "ideas", "specs", "tags", "item_tags",
        "related_links", "content_bundles", "publish_ledger", "reminders",
        "run_logs", "llm_cache",
    ]:
        assert t in tables, f"нет таблицы {t}"


def test_foreign_keys_enabled(tmp_path):
    conn = get_conn(tmp_path / "fk.db")
    init_db(tmp_path / "fk.db")
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_insert_idea_and_spec(tmp_path):
    conn = init_db(tmp_path / "idea.db")
    cur = conn.execute(
        "INSERT INTO ideas (title, summary, origin) VALUES (?, ?, 'research')",
        ("Test idea", "summary", ),
    )
    idea_id = cur.lastrowid
    conn.execute(
        "INSERT INTO specs (idea_id, path, status) VALUES (?, ?, 'draft')",
        (idea_id, "data/spec.md"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
    assert row["status"] == "new"
    assert row["origin"] == "research"
