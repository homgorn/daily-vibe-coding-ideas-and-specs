"""Synthesize: clustering → ideas → Viability Score → market trends.

Core pipeline: raw items → clusters → synthesized ideas with viability scoring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from engine.store.db import init_db
from engine.providers import complete, get_provider
from engine.store import write_note


@dataclass
class Cluster:
    id: int
    name: str
    item_ids: list[int]
    summary: str
    keywords: list[str]


@dataclass
class Idea:
    title: str
    summary: str
    origin: str
    source_url: str | None
    cluster_id: int
    viability: dict
    tags: list[str]
    related: list[int]
    content: str


def load_items_for_today(conn) -> list[dict]:
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT i.*, s.name as source_name
        FROM items i
        JOIN mentions m ON i.id = m.item_id
        JOIN sources s ON i.source_id = s.id
        WHERE m.day = ?
    """, (today,)).fetchall()
    return [dict(r) for r in rows]


def cluster_items(items: list[dict]) -> list[Cluster]:
    if not items:
        return []
    by_source: dict[str, list[int]] = {}
    for item in items:
        src = item.get("source_name") or item.get("source") or "other"
        by_source.setdefault(src, []).append(item["id"])
    clusters = []
    for i, (src, ids) in enumerate(by_source.items()):
        clusters.append(Cluster(
            id=i + 1,
            name=src.capitalize(),
            item_ids=ids,
            summary=f"Items from {src}",
            keywords=[src],
        ))
    return clusters


def synthesize_ideas(clusters: list[Cluster], items: list[dict]) -> list[Idea]:
    item_map = {item["id"]: item for item in items}
    ideas = []
    for cluster in clusters:
        cluster_items_list = [item_map[iid] for iid in cluster.item_ids if iid in item_map]
        if not cluster_items_list:
            continue
        first = cluster_items_list[0]
        title = first.get("title", "Untitled idea")
        summary = first.get("description", "")[:300] or first.get("title", "")
        src = (first.get("source_name") or first.get("source") or "").lower()
        ideas.append(Idea(
            title=title,
            summary=summary,
            origin="news" if src == "news" else "research",
            source_url=first.get("url"),
            cluster_id=cluster.id,
            viability={
                "market": 50, "competition": 50, "time_to_mvp": 50,
                "risk": 50, "score": 50, "confidence": 50,
            },
            tags=[cluster.name.lower().replace(" ", "-")],
            related=[],
            content=f"## Idea from {cluster.name}\n\n{summary}",
        ))
    return ideas


def save_clusters(conn, clusters: list[Cluster]) -> dict[int, int]:
    cluster_id_map = {}
    for cluster in clusters:
        row = conn.execute(
            "SELECT id FROM clusters WHERE name = ?", (cluster.name,)
        ).fetchone()
        if row:
            db_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO clusters (name, created_at) VALUES (?, datetime('now', 'localtime'))",
                (cluster.name,)
            )
            db_id = cur.lastrowid
        cluster_id_map[cluster.id] = db_id
        for item_id in cluster.item_ids:
            conn.execute(
                "INSERT OR IGNORE INTO item_clusters (item_id, cluster_id) VALUES (?, ?)",
                (item_id, db_id)
            )
    conn.commit()
    return cluster_id_map


def save_ideas(
    conn,
    ideas: list[Idea],
    cluster_map: dict[int, int],
    first_items: dict[int, int] | None = None,
) -> list[int]:
    idea_ids = []
    for idea in ideas:
        if idea.source_url:
            row = conn.execute(
                "SELECT id FROM ideas WHERE source_url = ?", (idea.source_url,)
            ).fetchone()
            if row:
                idea_ids.append(row["id"])
                continue
        viability_json = json.dumps(idea.viability, ensure_ascii=False)
        item_id = (first_items or {}).get(idea.cluster_id)
        cur = conn.execute("""
            INSERT INTO ideas (item_id, title, summary, origin, source_url, status, viability, created_at)
            VALUES (?, ?, ?, ?, ?, 'new', ?, datetime('now', 'localtime'))
        """, (item_id, idea.title, idea.summary, idea.origin,
              idea.source_url or "", viability_json))
        idea_id = cur.lastrowid
        idea_ids.append(idea_id)
        for tag in idea.tags:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
    conn.commit()
    return idea_ids


def write_idea_artifacts(ideas: list[Idea], idea_ids: list[int]):
    from engine.store import write_idea
    for idea, idea_id in zip(ideas, idea_ids):
        write_idea({
            "id": idea_id,
            "title": idea.title,
            "summary": idea.summary,
            "origin": idea.origin,
            "status": "new",
            "viability": idea.viability,
            "tags": idea.tags,
            "related": idea.related,
            "content": idea.content,
        })


def run_synthesis(config: dict) -> dict:
    conn = init_db()
    items = load_items_for_today(conn)
    if not items:
        return {"clusters": 0, "ideas": 0, "error": "No items for today"}

    clusters = cluster_items(items)
    cluster_map = save_clusters(conn, clusters)

    ideas = synthesize_ideas(clusters, items)
    first_items = {c.id: c.item_ids[0] for c in clusters if c.item_ids}
    idea_ids = save_ideas(conn, ideas, cluster_map, first_items)

    write_idea_artifacts(ideas, idea_ids)

    summary = f"# Synthesis Report {date.today().isoformat()}\n\n"
    summary += f"## Clusters ({len(clusters)})\n"
    for c in clusters:
        summary += f"- **{c.name}** ({len(c.item_ids)} items)\n"
    summary += f"\n## Ideas ({len(ideas)})\n"
    for idea, iid in zip(ideas, idea_ids):
        summary += f"- **{idea.title}** (ID: {iid})\n"
    write_note(summary, f"synthesis-{date.today().isoformat()}", "synthesis")

    return {"clusters": len(clusters), "ideas": len(ideas), "idea_ids": idea_ids}