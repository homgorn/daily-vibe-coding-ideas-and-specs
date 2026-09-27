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


# Section headings in the inbox that describe how to use the file rather than
# hold ideas. Parsing them turns the instructions into "ideas".
INSTRUCTION_SECTIONS = {
    "правила", "rules", "инструкция", "как пользоваться", "how to use",
    "формат", "format", "архив", "заархивировано", "archive", "processed",
}

# Lines that are examples or empty slots, not submissions. Deliberately keyed
# on prose, not on domains: a real submission may legitimately link example.com.
PLACEHOLDER_MARKERS = (
    "пусто", "добавь первую", "placeholder", "твой пример", "your example",
    "замените", "replace me", "здесь будет", "your link here",
)

_CHECKBOX_LINE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+)$")
_URL_ONLY = re.compile(r"^(https?://\S+)$")


def _is_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _title_from_url(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1] or url
    return tail.replace("-", " ").replace("_", " ").strip() or url


def parse_inbox() -> list[IngestItem]:
    """Parse ingest/inbox.md for user-submitted items.

    Two supported shapes, both taken from the inbox's own instructions:

    Checklist line (the documented format):
        - [ ] https://github.com/owner/repo | short description

    Key/value block:
        ## Title
        URL: https://...
        Description: ...
        tags: tag1, tag2

    Instruction sections, archived entries, and placeholder/example lines are
    skipped: the template that ships in the repo must not manufacture ideas.
    """
    if not INBOX_PATH.exists():
        return []

    content = INBOX_PATH.read_text(encoding="utf-8")
    items: list[IngestItem] = []

    for section in re.split(r"^## ", content, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        if heading.lower().strip("# ").strip() in INSTRUCTION_SECTIONS:
            continue

        pending: list[IngestItem] = []
        kv: dict[str, str] = {}
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue

            checkbox = _CHECKBOX_LINE.match(stripped)
            if checkbox:
                body = checkbox.group(2).strip()
                if _is_placeholder(body):
                    continue
                url, _, description = body.partition("|")
                url = url.strip()
                description = description.strip()
                if not _URL_ONLY.match(url):
                    # Not a link line — treat the whole body as the title.
                    url, description = "", body
                pending.append(IngestItem(
                    title=_title_from_url(url) if url else body[:80],
                    url=url or None,
                    description=description,
                    origin="user",
                    raw=stripped,
                ))
                continue

            key = stripped.split(":", 1)[0].strip().lower()
            if key in ("tags", "url", "description", "desc", "title") and ":" in stripped:
                kv[key] = stripped.split(":", 1)[1].strip()
                continue

            if _URL_ONLY.match(stripped):
                kv.setdefault("url", stripped)
                continue

            if not _is_placeholder(stripped):
                kv.setdefault("description", stripped)

        if pending:
            items.extend(pending)
            continue

        title = kv.get("title") or heading
        url = kv.get("url") or ""
        if not url and not kv.get("description"):
            continue
        if _is_placeholder(f"{title} {url} {kv.get('description', '')}"):
            continue
        tags = [t.strip() for t in kv.get("tags", "").split(",") if t.strip()]
        items.append(IngestItem(
            title=title or _title_from_url(url),
            url=url or None,
            description=kv.get("description", ""),
            origin="user",
            tags=tags,
            raw="\n".join(lines).strip(),
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