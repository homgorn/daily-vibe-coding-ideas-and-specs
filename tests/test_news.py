"""Tests for news module: RSS parsing, storage, analysis."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.news import (
    NewsItem,
    parse_feed,
    store_news,
    analyze_news,
    mark_news_processed,
    NEWS_RSS_FEEDS,
)
from engine.store.db import init_db


def test_news_rss_feeds_configured():
    assert len(NEWS_RSS_FEEDS) >= 3
    for feed in NEWS_RSS_FEEDS:
        assert "name" in feed
        assert "url" in feed
        assert feed["url"].startswith("https://")


def test_store_news(tmp_path):
    conn = init_db(tmp_path / "news.db")
    items = [
        NewsItem(
            headline="AI Agent Framework Released",
            source_name="TechCrunch",
            url="https://techcrunch.com/ai-agent",
            published_at="2026-09-24",
            summary="New framework for building AI agents",
        ),
        NewsItem(
            headline="LLM Benchmark Results",
            source_name="The Verge",
            url="https://theverge.com/llm-bench",
            published_at="2026-09-24",
            summary="Latest benchmark comparison",
        ),
    ]
    stats = store_news(conn, items)
    assert stats["new"] == 2
    assert stats["dup"] == 0

    # Store again - should be duplicates
    stats2 = store_news(conn, items)
    assert stats2["dup"] == 2

    # Check DB
    row = conn.execute("SELECT COUNT(*) as c FROM news_items").fetchone()
    assert row["c"] == 2


def test_analyze_news(tmp_path):
    conn = init_db(tmp_path / "news2.db")
    items = [
        NewsItem(
            headline="Test Headline",
            source_name="Test",
            url="https://example.com/1",
            published_at="2026-09-24",
            summary="Test summary",
        ),
    ]
    store_news(conn, items)

    # All unprocessed
    to_analyze = analyze_news(conn)
    assert len(to_analyze) == 1
    assert to_analyze[0]["headline"] == "Test Headline"

    # Mark processed
    mark_news_processed(conn, [to_analyze[0]["id"]])
    to_analyze2 = analyze_news(conn)
    assert len(to_analyze2) == 0


def test_parse_feed_invalid_url():
    """Invalid URL returns empty list, no exception."""
    items = parse_feed("https://nonexistent.invalid/feed.xml", "Test")
    assert items == []


def test_news_item_dataclass():
    item = NewsItem(
        headline="Test",
        source_name="Test Source",
        url="https://example.com",
        published_at="2026-09-24",
        summary="Summary",
    )
    assert item.headline == "Test"
    assert item.source_name == "Test Source"