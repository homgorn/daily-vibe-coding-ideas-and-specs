"""fetch: GitHub API (search/trending), Hacker News, Reddit RSS, npm, RSS-блоги.

Фаза 1: github + hn + ингест в БД с дедупом по fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.store.db import init_db  # noqa: E402


@dataclass
class FetchedItem:
    title: str
    url: str
    source: str
    description: str = ""
    meta: dict = field(default_factory=dict)


def fingerprint(title: str, url: str, source: str) -> str:
    normalized_url = url.strip().lower().rstrip('/')
    raw = f"{source}|{title.strip().lower()}|{normalized_url}"
    return hashlib.sha256(raw.encode()).hexdigest()


def ensure_source(conn, name: str, kind: str, url: str = "") -> int:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO sources (name, kind, url) VALUES (?, ?, ?)", (name, kind, url)
    )
    conn.commit()
    return cur.lastrowid


def store_items(conn, items: list[FetchedItem]) -> dict:
    """Сохраняет только новые (INSERT OR IGNORE по fingerprint) + день в mentions."""
    stats = {"new": 0, "dup": 0, "failed": 0}
    today = date.today().isoformat()
    for item in items:
        fp = fingerprint(item.title, item.url, item.source)
        source_id = ensure_source(conn, item.source, "github" if "github" in item.source else "web")
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO items (fingerprint, source_id, title, url, description, meta, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (fp, source_id, item.title, item.url, item.description,
                 json.dumps(item.meta, ensure_ascii=False)),
            )
            if cur.rowcount == 0:
                stats["dup"] += 1
                continue
            item_id = cur.lastrowid
            conn.execute(
                "INSERT OR IGNORE INTO mentions (item_id, day) VALUES (?, ?)", (item_id, today)
            )
            stats["new"] += 1
        except Exception:  # noqa: BLE001
            stats["failed"] += 1
    conn.commit()
    return stats


def _gh_api(url: str, token: str | None) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "DailyVibeEngine/0.1")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_github(token: str | None = None, days_back: int = 7) -> list[FetchedItem]:
    """Топ-репозитории: свежие + по темам (vibe-coding, ai-agents, llm, mcp, ai-tools)."""
    topics = ["vibe-coding", "ai-agents", "llm", "mcp", "ai-tools", "ai-agents-framework"]
    since = (date.today() - timedelta(days=days_back)).isoformat()
    items: list[FetchedItem] = []
    seen: set[str] = set()

    def add_repo(r: dict, why: str) -> None:
        full = r.get("full_name", "")
        if full in seen:
            return
        seen.add(full)
        items.append(FetchedItem(
            title=f"{full} — {r.get('description') or r.get('name')}".strip(" —"),
            url=r.get("html_url", ""),
            source="github",
            description=r.get("description") or "",
            meta={
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language"),
                "topics": r.get("topics", []),
                "fork": r.get("fork", False),
                "created": r.get("created_at", ""),
                "pushed": r.get("pushed_at", ""),
                "why": why,
            },
        ))

    queries = [
        f"stars:>100 created:>{since} sort:stars",
        f"topic:vibe-coding stars:>10",
        f"topic:ai-agents stars:>50",
        f"topic:mcp stars:>20",
        f"topic:llm stars:>200 pushed:>{since}",
    ]
    for q in queries:
        url = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(q) + "&per_page=15"
        try:
            data = _gh_api(url, token)
        except Exception:  # noqa: BLE001
            continue
        for r in data.get("items", []):
            add_repo(r, q)

    try:
        data = _gh_api(
            "https://api.github.com/search/repositories?q=stars:>500&sort=updated&order=desc&per_page=10",
            token,
        )
        for r in data.get("items", []):
            add_repo(r, "updated-recent")
    except Exception:  # noqa: BLE001
        pass

    return items


def fetch_hacker_news() -> list[FetchedItem]:
    """Top HN-посты дня (без API-ключа)."""
    items: list[FetchedItem] = []
    try:
        with urllib.request.urlopen(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=30
        ) as resp:
            ids = json.loads(resp.read().decode())[:40]
        for story_id in ids:
            with urllib.request.urlopen(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=30
            ) as resp:
                story = json.loads(resp.read().decode())
            if not story or not story.get("title"):
                continue
            items.append(FetchedItem(
                title=story["title"],
                url=story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                source="hn",
                description=story.get("text") or "",
                meta={"score": story.get("score", 0), "hn_id": story_id},
            ))
    except Exception:  # noqa: BLE001
        pass
    return items


def fetch_all(config: dict, token: str | None = None) -> dict:
    """Собирает всё включённое, раскладывает по источникам, сохраняет в БД."""
    conn = init_db()
    results: dict[str, int] = {}

    if config.get("sources", {}).get("github_trending"):
        items = fetch_github(token=token)
        results["github"] = store_items(conn, items)["new"]

    if config.get("sources", {}).get("hackernews"):
        items = fetch_hacker_news()
        results["hn"] = store_items(conn, items)["new"]

    return results