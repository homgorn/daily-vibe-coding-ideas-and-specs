"""Store: MD mirror writing + SQLite persistence.

MD = source of truth for humans, SQLite = source of truth for machines.
All artifacts written to typed folders under data/YYYY-MM-DD/ and publish/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
PUBLISH_DIR = ROOT / "publish"
KNOWLEDGE_DIR = ROOT / "knowledge"


def ensure_dirs():
    """Create all required directories."""
    for d in [DATA_DIR, PUBLISH_DIR, KNOWLEDGE_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    # Daily dirs
    today = date.today().isoformat()
    (DATA_DIR / today / "raw").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / today / "notes").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / today / "specs").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / today / "prompts").mkdir(parents=True, exist_ok=True)
    # Publish dirs
    for lang in ["en", "ru"]:
        (PUBLISH_DIR / lang / "ideas").mkdir(parents=True, exist_ok=True)
        (PUBLISH_DIR / lang / "specs").mkdir(parents=True, exist_ok=True)
        (PUBLISH_DIR / lang / "rankings").mkdir(parents=True, exist_ok=True)
        (PUBLISH_DIR / lang / "courses").mkdir(parents=True, exist_ok=True)


def write_raw_items(items: list[dict], source: str) -> Path:
    """Write raw fetched items to data/YYYY-MM-DD/raw/{source}.jsonl"""
    ensure_dirs()
    today = date.today().isoformat()
    path = DATA_DIR / today / "raw" / f"{source}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return path


def safe_name(text: str, max_len: int = 80) -> str:
    """ASCII-only filename stem: transliterate accents, drop non-latin, hash if empty."""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()
    slug = slug[:max_len].strip("-")
    if slug:
        return slug
    digest = hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:8]
    return f"untitled-{digest}"


def drop_stale_siblings(path: Path) -> list[Path]:
    """Remove same-id artifact files next to `path` (slug rules changed over time)."""
    if not path.parent.exists():
        return []
    prefix = path.stem.split("_", 1)[0] + "_"
    removed = []
    for sibling in sorted(path.parent.glob(f"{prefix}*.md")):
        if sibling.name != path.name and sibling.is_file():
            sibling.unlink()
            removed.append(sibling)
    return removed


def _base_url() -> str:
    from engine.config import load_config

    return str(load_config().get("site", {}).get("base_url", "https://example.com")).rstrip("/")


def write_note(content: str, title: str, category: str = "general") -> Path:
    """Write a note to data/YYYY-MM-DD/notes/"""
    ensure_dirs()
    today = date.today().isoformat()
    safe_title = safe_name(title)
    path = DATA_DIR / today / "notes" / f"{category}_{safe_title}.md"
    frontmatter = f"""---
title: "{title}"
category: {category}
date: {today}
origin: research
---
"""
    with path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)
    return path


def write_spec(
    idea_id: int,
    title: str,
    spec_md: str,
    viability: dict,
    tags: list[str] | None = None,
    description: str | None = None,
) -> Path:
    """Write spec to data/YYYY-MM-DD/specs/ and publish/en/specs/"""
    ensure_dirs()
    today = date.today().isoformat()
    safe_title = safe_name(title)
    tags = tags or []
    tags_json = json.dumps(tags, ensure_ascii=False)
    short_title = title if len(title) <= 70 else title[:67].rstrip() + "..."
    desc = description or viability.get("description", "") or f"Spec for {short_title}"
    desc = desc if len(desc) <= 160 else desc[:157].rstrip() + "..."
    short_title = short_title.replace('"', "'")
    desc = desc.replace('"', "'")

    frontmatter = f"""---
title: "{short_title}"
description: "{desc}"
tags: {tags_json}
idea_id: {idea_id}
date: {today}
viability_score: {viability.get('score', 0)}
viability_confidence: {viability.get('confidence', 0)}
status: draft
origin: research
canonical: {_base_url()}/specs/{idea_id}
---
"""
    # Data mirror
    data_path = DATA_DIR / today / "specs" / f"{idea_id}_{safe_title}.md"
    with data_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + spec_md)

    # Publish mirror (EN)
    pub_path = PUBLISH_DIR / "en" / "specs" / f"{idea_id}_{safe_title}.md"
    with pub_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + spec_md)

    drop_stale_siblings(data_path)
    drop_stale_siblings(pub_path)

    return data_path


def write_idea(idea: dict) -> Path:
    """Write idea to data/YYYY-MM-DD/notes/ and publish/en/ideas/"""
    ensure_dirs()
    today = date.today().isoformat()
    idea_id = idea.get("id", 0)
    title = idea.get("title", "untitled").replace('"', "'")
    safe_title = safe_name(title)

    frontmatter = f"""---
idea_id: {idea_id}
title: "{title}"
summary: "{idea.get('summary', '').replace('"', '\\"')}"
origin: {idea.get('origin', 'research')}
status: {idea.get('status', 'new')}
viability_score: {idea.get('viability', {}).get('score', 0)}
viability_confidence: {idea.get('viability', {}).get('confidence', 0)}
tags: {json.dumps(idea.get('tags', []), ensure_ascii=False)}
related: {json.dumps(idea.get('related', []), ensure_ascii=False)}
date: {today}
---
"""
    content = idea.get("content", "")

    # Data mirror
    data_path = DATA_DIR / today / "notes" / f"idea_{idea_id}_{safe_title}.md"
    with data_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)

    # Publish mirror (EN)
    pub_path = PUBLISH_DIR / "en" / "ideas" / f"{idea_id}_{safe_title}.md"
    with pub_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)

    drop_stale_siblings(data_path)
    drop_stale_siblings(pub_path)

    return data_path


def write_ranking(ranking: dict) -> Path:
    """Write ranking/listicle to publish/en/rankings/"""
    ensure_dirs()
    today = date.today().isoformat()
    title = ranking.get("title", "ranking")
    safe_title = safe_name(title)

    frontmatter = f"""---
title: "{title}"
type: ranking
date: {today}
criteria: {json.dumps(ranking.get('criteria', {}), ensure_ascii=False)}
items_count: {len(ranking.get('items', []))}
---
"""
    content = ranking.get("content", "")

    pub_path = PUBLISH_DIR / "en" / "rankings" / f"{today}_{safe_title}.md"
    with pub_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)

    return pub_path


def write_course_lesson(lesson: dict) -> Path:
    """Write course lesson to publish/en/courses/"""
    ensure_dirs()
    today = date.today().isoformat()
    title = lesson.get("title", "lesson")
    safe_title = safe_name(title)

    frontmatter = f"""---
title: "{title}"
course: "{lesson.get('course', 'Vibe Coding 101')}"
lesson_number: {lesson.get('lesson_number', 1)}
date: {today}
tags: {json.dumps(lesson.get('tags', []), ensure_ascii=False)}
---
"""
    content = lesson.get("content", "")

    pub_path = PUBLISH_DIR / "en" / "courses" / f"{lesson.get('lesson_number', 1):02d}_{safe_title}.md"
    with pub_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + content)

    return pub_path


def read_raw_items(source: str, day: str | None = None) -> list[dict]:
    """Read raw items from data/YYYY-MM-DD/raw/{source}.jsonl"""
    if day is None:
        day = date.today().isoformat()
    path = DATA_DIR / day / "raw" / f"{source}.jsonl"
    if not path.exists():
        return []
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def get_today_dir() -> Path:
    """Get today's data directory."""
    ensure_dirs()
    return DATA_DIR / date.today().isoformat()