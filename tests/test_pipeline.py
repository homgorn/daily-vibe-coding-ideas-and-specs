"""Integration test: full pipeline offline (no network, tmp dirs)."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.store.db as db_mod
import engine.store as store_mod
import engine.index as index_mod
import engine.providers as providers_mod
import engine.fetch as fetch_mod
import engine.news as news_mod
import engine.publish.site as site_mod
from engine.config import load_config
from engine.store.db import init_db


def test_full_pipeline_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "engine.db")
    monkeypatch.setattr(store_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(store_mod, "PUBLISH_DIR", tmp_path / "publish")
    monkeypatch.setattr(index_mod, "INDEX_DIR", tmp_path / "index")
    monkeypatch.setattr(index_mod, "PUBLISH_DIR", tmp_path / "publish")
    monkeypatch.setattr(site_mod, "SITE_DIR", tmp_path / "site")

    cfg = copy.deepcopy(load_config())
    cfg["cache"] = {"llm_path": str(tmp_path / "llm_cache.sqlite"), "llm_enabled": True}
    cfg["knowledge"] = {"auto_index_on_run": False}
    cfg["models"] = {**cfg.get("models", {}), "provider": "mock"}
    monkeypatch.setattr("engine.config.load_config", lambda: cfg)
    monkeypatch.setattr("cli.load_config", lambda: cfg)
    monkeypatch.setattr(providers_mod, "_registry", None)

    from engine.fetch import FetchedItem, store_items

    def fake_fetch_all(config, token=None):
        conn = init_db()
        items = [
            FetchedItem(
                title=f"AI agent tool for developers {i}",
                url=f"https://example.com/ai-agent-tool-{i}",
                source="github" if i % 2 else "hn",
                description="Open-source tool for building LLM agents",
                meta={},
            )
            for i in range(10)
        ]
        return {"fake": store_items(conn, items)["new"]}

    monkeypatch.setattr(fetch_mod, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(
        news_mod, "run_news",
        lambda config: {"fetched": 0, "stored": 0, "analyzed": 0},
    )

    import cli

    rc = cli.cmd_run(argparse.Namespace())
    assert rc == 0

    conn = init_db()
    row = conn.execute(
        "SELECT status, details FROM run_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row["status"] == "ok"

    details = json.loads(row["details"])
    assert details["fetch"]["fake"] == 10
    assert details["synthesize"]["ideas"] >= 1
    assert details["spec"]["specs"] >= 1
    # The mock provider cannot return valid JSON, so every spec is a
    # generation failure and must be rejected by validation. That is the
    # point: nothing half-generated is ever publishable.
    assert details["validate"]["failed"] >= 1
    assert details["validate"]["passed"] == 0

    specs = list((tmp_path / "publish" / "en" / "specs").glob("*.md"))
    assert specs, "specs must be written to tmp publish dir"

    assert (tmp_path / "index" / "INDEX.md").exists()
    assert list((tmp_path / "index" / "ideas").glob("idea_*.md"))
    assert (tmp_path / "data").exists()
    assert (tmp_path / "llm_cache.sqlite").exists()


def test_pipeline_dedupes_across_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "engine.db")
    monkeypatch.setattr(store_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(store_mod, "PUBLISH_DIR", tmp_path / "publish")
    monkeypatch.setattr(index_mod, "INDEX_DIR", tmp_path / "index")
    monkeypatch.setattr(index_mod, "PUBLISH_DIR", tmp_path / "publish")
    monkeypatch.setattr(site_mod, "SITE_DIR", tmp_path / "site")

    cfg = copy.deepcopy(load_config())
    cfg["cache"] = {"llm_path": str(tmp_path / "llm_cache.sqlite"), "llm_enabled": True}
    cfg["models"] = {**cfg.get("models", {}), "provider": "mock"}
    monkeypatch.setattr("engine.config.load_config", lambda: cfg)
    monkeypatch.setattr("cli.load_config", lambda: cfg)
    monkeypatch.setattr(providers_mod, "_registry", None)

    from engine.fetch import FetchedItem, store_items

    def fake_fetch_all(config, token=None):
        conn = init_db()
        items = [
            FetchedItem(
                title="Same item title",
                url="https://example.com/same-item/",
                source="github",
                description="x",
                meta={},
            )
        ]
        return {"fake": store_items(conn, items)["new"]}

    monkeypatch.setattr(fetch_mod, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(
        news_mod, "run_news",
        lambda config: {"fetched": 0, "stored": 0, "analyzed": 0},
    )

    import cli

    assert cli.cmd_run(argparse.Namespace()) == 0
    conn = init_db()
    first = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]

    # trailing slash + same title on second run → deduped
    assert cli.cmd_run(argparse.Namespace()) == 0
    second = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    assert second == first
