"""fetch: fingerprint, сохранение в БД, дедуп между прогонами (без сети)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.fetch import (  # noqa: E402
    FetchedItem,
    fingerprint,
    store_items,
)
from engine.store.db import init_db  # noqa: E402


def test_fingerprint_stable_and_unique():
    a = fingerprint("Foo Bar", "https://x.com/a", "github")
    b = fingerprint("foo bar ", "https://x.com/a/", "github")
    c = fingerprint("Foo Bar", "https://x.com/a", "hn")
    assert a == b
    assert a != c


def test_store_items_and_dedup(tmp_path):
    conn = init_db(tmp_path / "fetch.db")
    items = [FetchedItem("Repo One", "https://github.com/o/r", "github", meta={"stars": 10})]
    first = store_items(conn, items)
    second = store_items(conn, items)
    assert first["new"] == 1
    assert second["dup"] == 1

    row = conn.execute("SELECT * FROM items").fetchone()
    assert row["title"] == "Repo One"

    mentions = conn.execute("SELECT COUNT(*) AS c FROM mentions").fetchone()["c"]
    assert mentions == 1


def test_store_items_different_sources_both_kept(tmp_path):
    conn = init_db(tmp_path / "fetch2.db")
    items = [
        FetchedItem("Same Title", "https://a.com/1", "github"),
        FetchedItem("Same Title", "https://a.com/1", "hn"),
    ]
    stats = store_items(conn, items)
    assert stats["new"] == 2