"""Ingest: manual input processing (inbox.md, add-idea, candidates/).

Parses user-provided notes, links, screenshots into pipeline-ready items.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INBOX_PATH = ROOT / "ingest" / "inbox.md"
CANDIDATES_DIR = ROOT / "candidates"
MANUAL_DIR = ROOT / "manual"


@dataclass
class IngestItem:
    title: str
    url: str | None = None
    description: str = ""
    origin: str = "user"
    tags: list[str] = field(default_factory=list)
    raw: str = ""


def parse_inbox() -> list[IngestItem]:
    """Parse ingest/inbox.md for user-submitted items.

    Format:
    ## Title
    URL: https://...
    Description: ...
    tags: tag1, tag2

    Or just a URL on its own line.
    """
    if not INBOX_PATH.exists():
        return []

    content = INBOX_PATH.read_text(encoding="utf-8")
    items = []

    # Split by ## headings
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for section in sections[1:]:  # Skip first (before first ##)
        lines = section.strip().splitlines()
        if not lines:
            continue

        title = lines[0].strip()
        url = None
        description = ""
        tags = []

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # URL pattern
            url_match = re.search(r"(https?://\S+)", line)
            if url_match and not url:
                url = url_match.group(1)

            # tags: pattern
            if line.lower().startswith("tags:"):
                tags_str = line[5:].strip()
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                continue

            # description: pattern
            if line.lower().startswith(("description:", "desc:")):
                description = line.split(":", 1)[1].strip()
                continue

            # Bare URL line
            if re.match(r"^https?://\S+$", line):
                if not url:
                    url = line
                continue

            # Otherwise accumulate as description
            if description:
                description += " " + line
            else:
                description = line

        if title or url:
            items.append(IngestItem(
                title=title or (url or "Untitled"),
                url=url,
                description=description,
                origin="user",
                tags=tags,
                raw=section.strip(),
            ))

    return items


def parse_candidates() -> list[IngestItem]:
    """Parse candidates/ directory for candidate ideas."""
    if not CANDIDATES_DIR.exists():
        return []

    items = []
    for md_file in sorted(CANDIDATES_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        title = md_file.stem.replace("-", " ").replace("_", " ").title()

        # Extract URL
        url_match = re.search(r"(https?://\S+)", content)
        url = url_match.group(1) if url_match else None

        # Extract tags
        tags = []
        tags_match = re.search(r"tags:\s*\[([^\]]+)\]", content)
        if tags_match:
            tags = [t.strip().strip("'\"") for t in tags_match.group(1).split(",")]

        items.append(IngestItem(
            title=title,
            url=url,
            description=content[:500],
            origin="user",
            tags=tags,
            raw=content,
        ))

    return items


def parse_manual_ideas() -> list[IngestItem]:
    """Parse manual/ directory for owner-added ideas."""
    if not MANUAL_DIR.exists():
        return []

    items = []
    for md_file in sorted(MANUAL_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        # Extract title from frontmatter or first heading
        title = ""
        fm_match = re.search(r'title:\s*"([^"]+)"', content)
        if fm_match:
            title = fm_match.group(1)
        else:
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()

        # Extract URL
        url_match = re.search(r"(https?://\S+)", content)
        url = url_match.group(1) if url_match else None

        # Extract tags
        tags = []
        tags_match = re.search(r"tags:\s*\[([^\]]+)\]", content)
        if tags_match:
            tags = [t.strip().strip("'\"") for t in tags_match.group(1).split(",")]

        items.append(IngestItem(
            title=title or md_file.stem,
            url=url,
            description=content[:500],
            origin="user",
            tags=tags,
            raw=content,
        ))

    return items


def process_inbox(conn=None) -> dict:
    """Process all ingest sources into pipeline items.

    Returns stats about processed items.
    """
    stats = {"inbox": 0, "candidates": 0, "manual": 0, "total": 0, "new": 0}

    all_items = []

    # Inbox
    inbox_items = parse_inbox()
    stats["inbox"] = len(inbox_items)
    all_items.extend(inbox_items)

    # Candidates
    cand_items = parse_candidates()
    stats["candidates"] = len(cand_items)
    all_items.extend(cand_items)

    # Manual ideas
    manual_items = parse_manual_ideas()
    stats["manual"] = len(manual_items)
    all_items.extend(manual_items)

    stats["total"] = len(all_items)

    # Store in DB if connection provided
    if conn and all_items:
        from engine.fetch import FetchedItem, store_items
        fetched = [
            FetchedItem(
                title=item.title,
                url=item.url or "",
                source="ingest",
                description=item.description,
                meta={"origin": item.origin, "tags": item.tags, "raw": item.raw[:1000]},
            )
            for item in all_items
        ]
        result = store_items(conn, fetched)
        stats["new"] = result["new"]

    return stats


def add_idea_interactive(conn) -> dict:
    """Interactive idea entry via CLI (add-idea command)."""
    print("=== Добавление идеи ===")
    title = input("Название: ").strip()
    if not title:
        return {"error": "No title provided"}

    url = input("URL (или пусто): ").strip() or None
    summary = input("Краткое описание: ").strip()
    tags_str = input("Теги (через запятую): ").strip()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    import json as _json
    from datetime import datetime

    viability = _json.dumps({
        "market": 50, "competition": 50, "time_to_mvp": 50,
        "risk": 50, "score": 50, "confidence": 50,
    })

    cur = conn.execute("""
        INSERT INTO ideas (title, summary, origin, source_url, status, viability, created_at)
        VALUES (?, ?, 'user', ?, 'new', ?, datetime('now'))
    """, (title, summary, url or "", viability))
    idea_id = cur.lastrowid

    # Tags
    for tag in tags:
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
        if tag_row:
            conn.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (idea_id, tag_row["id"])
            )

    conn.commit()

    # Write MD artifact
    from engine.store import write_idea
    write_idea({
        "id": idea_id,
        "title": title,
        "summary": summary,
        "origin": "user",
        "status": "new",
        "viability": {"score": 50, "confidence": 50},
        "tags": tags,
        "related": [],
        "content": f"# {title}\n\n{summary}",
    })

    print(f"Идея добавлена: ID={idea_id}")
    return {"id": idea_id, "title": title, "tags": tags}