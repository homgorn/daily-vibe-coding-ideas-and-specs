"""News: parse news feeds → analyze → generate ideas.

Fetches news from RSS feeds, stores in news_items, triggers idea synthesis.
"""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from engine.store.db import init_db
from engine.fetch import FetchedItem, store_items


@dataclass
class NewsItem:
    headline: str
    source_name: str
    url: str
    published_at: str
    summary: str


NEWS_RSS_FEEDS = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Hacker News Best", "url": "https://hnrss.org/best"},
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/"},
]


def parse_feed(feed_url: str, source_name: str) -> list[NewsItem]:
    """Parse a single RSS/Atom feed."""
    items = []
    try:
        req = urllib.request.Request(feed_url)
        req.add_header("User-Agent", "DailyVibeEngine/0.1")
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_content = resp.read().decode(errors="replace")

        root = ET.fromstring(xml_content)

        # RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            if title and link:
                items.append(NewsItem(
                    headline=title.strip(),
                    source_name=source_name,
                    url=link.strip(),
                    published_at=pub_date.strip(),
                    summary=desc.strip()[:500],
                ))

        # Atom
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(f".//{atom_ns}entry"):
            title = entry.findtext(f"{atom_ns}title", "")
            link_elem = entry.find(f"{atom_ns}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            summary = entry.findtext(f"{atom_ns}summary", "") or entry.findtext(f"{atom_ns}content", "")
            published = entry.findtext(f"{atom_ns}published", "") or entry.findtext(f"{atom_ns}updated", "")

            if title and link:
                items.append(NewsItem(
                    headline=title.strip(),
                    source_name=source_name,
                    url=link.strip(),
                    published_at=published.strip(),
                    summary=(summary or "").strip()[:500],
                ))

    except Exception:
        pass
    return items


def fetch_news(feeds: list[dict] | None = None) -> list[NewsItem]:
    """Fetch news from all configured feeds."""
    if feeds is None:
        feeds = NEWS_RSS_FEEDS
    all_items = []
    for feed in feeds:
        items = parse_feed(feed["url"], feed["name"])
        all_items.extend(items)
    return all_items


def store_news(conn, news_items: list[NewsItem]) -> dict:
    """Store news items in DB (news_items table + items table for dedup)."""
    stats = {"new": 0, "dup": 0, "failed": 0}

    # Also store in items for unified dedup
    fetched = [
        FetchedItem(
            title=n.headline,
            url=n.url,
            source="news",
            description=n.summary,
            meta={"source_name": n.source_name, "published": n.published_at},
        )
        for n in news_items
    ]
    item_stats = store_items(conn, fetched)

    # Store in news_items
    for n in news_items:
        try:
            existing = conn.execute(
                "SELECT id FROM news_items WHERE url = ?", (n.url,)
            ).fetchone()
            if existing:
                stats["dup"] += 1
                continue
            conn.execute(
                "INSERT INTO news_items (headline, source_name, url, published_at, summary, processed) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (n.headline, n.source_name, n.url, n.published_at, n.summary),
            )
            stats["new"] += 1
        except Exception:
            stats["failed"] += 1

    conn.commit()
    stats["items_new"] = item_stats["new"]
    return stats


def analyze_news(conn, limit: int = 20) -> list[dict]:
    """Get unprocessed news for analysis."""
    rows = conn.execute("""
        SELECT id, headline, source_name, url, published_at, summary
        FROM news_items
        WHERE processed = 0
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def mark_news_processed(conn, news_ids: list[int]):
    """Mark news items as processed."""
    for nid in news_ids:
        conn.execute("UPDATE news_items SET processed = 1 WHERE id = ?", (nid,))
    conn.commit()


def run_news(config: dict) -> dict:
    """Full news pipeline: fetch → store → analyze."""
    conn = init_db()

    # Fetch
    news_items = fetch_news()
    if not news_items:
        return {"fetched": 0, "stored": 0, "analyzed": 0}

    # Store
    store_stats = store_news(conn, news_items)

    # Analyze unprocessed
    to_analyze = analyze_news(conn)
    mark_news_processed(conn, [n["id"] for n in to_analyze])

    return {
        "fetched": len(news_items),
        "stored": store_stats["new"],
        "dup": store_stats["dup"],
        "analyzed": len(to_analyze),
        "headlines": [n["headline"] for n in to_analyze[:5]],
    }