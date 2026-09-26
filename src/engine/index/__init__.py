"""Multi-level Markdown indexes: global → day → category → cluster → tag → idea.

Everything indexed: every artifact gets its own INDEX.md.
Cross-linking via related_links table.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = ROOT / "index"
PUBLISH_DIR = ROOT / "publish"
KNOWLEDGE_DIR = ROOT / "knowledge"


def ensure_index_dirs():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["days", "categories", "clusters", "tags", "ideas"]:
        (INDEX_DIR / sub).mkdir(parents=True, exist_ok=True)


def _prune(subdir: str, keep: list[Path]) -> int:
    """Delete generated index files in subdir that were not rebuilt this run."""
    d = INDEX_DIR / subdir
    if not d.exists():
        return 0
    keep_set = {p.resolve() for p in keep}
    removed = 0
    for p in sorted(d.glob("*.md")):
        if p.resolve() not in keep_set:
            p.unlink()
            removed += 1
    return removed


def _rel_link(target: Path, depth: int) -> str:
    """Repo-relative POSIX link target, prefixed with ../ * depth."""
    try:
        rel = target.resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        rel = target.name
    return "../" * depth + rel


def _prune_days(conn) -> int:
    """Delete day index pages for days that have no items left."""
    d = INDEX_DIR / "days"
    if not d.exists():
        return 0
    removed = 0
    for p in sorted(d.glob("*.md")):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem):
            continue
        cnt = conn.execute(
            "SELECT COUNT(*) AS c FROM mentions WHERE day = ?", (p.stem,)
        ).fetchone()["c"]
        if cnt == 0:
            p.unlink()
            removed += 1
    return removed


def build_global_index(conn) -> Path:
    """Build INDEX.md — global index of everything."""
    ensure_index_dirs()

    # Counts
    counts = {}
    for table in ["items", "ideas", "specs", "clusters", "tags"]:
        counts[table] = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]

    # Recent ideas
    recent_ideas = conn.execute("""
        SELECT id, title, status, viability, created_at
        FROM ideas ORDER BY created_at DESC LIMIT 20
    """).fetchall()

    # Active clusters
    clusters = conn.execute("""
        SELECT c.id, c.name, COUNT(ic.item_id) as cnt
        FROM clusters c
        LEFT JOIN item_clusters ic ON c.id = ic.cluster_id
        GROUP BY c.id ORDER BY cnt DESC LIMIT 15
    """).fetchall()

    # Popular tags
    tags = conn.execute("""
        SELECT t.name, COUNT(it.item_id) as cnt
        FROM tags t
        LEFT JOIN item_tags it ON t.id = it.tag_id
        GROUP BY t.id ORDER BY cnt DESC LIMIT 30
    """).fetchall()

    # Days with data
    days = conn.execute("""
        SELECT day, COUNT(*) as cnt
        FROM mentions GROUP BY day ORDER BY day DESC LIMIT 30
    """).fetchall()

    lines = [
        "# Global Index",
        f"\n*Updated: {datetime.now().isoformat(timespec='seconds')}*\n",
        "## Statistics",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Items | {counts['items']} |",
        f"| Ideas | {counts['ideas']} |",
        f"| Specs | {counts['specs']} |",
        f"| Clusters | {counts['clusters']} |",
        f"| Tags | {counts['tags']} |",
        "",
        "## Recent Ideas",
        "",
    ]

    for idea in recent_ideas:
        viability = json.loads(idea["viability"]) if idea["viability"] else {}
        score = viability.get("score", "?")
        lines.append(
            f"- [{idea['title']}](ideas/idea_{idea['id']}.md) — "
            f"**{score}**/100 — `{idea['status']}` — {idea['created_at'][:10]}"
        )

    lines.append("\n## Clusters\n")
    for c in clusters:
        lines.append(f"- [{c['name']}](clusters/cluster_{c['id']}.md) ({c['cnt']} items)")

    lines.append("\n## Tags\n")
    tag_links = [f"[{t['name']}](tags/tag_{t['name']}.md) ({t['cnt']})" for t in tags]
    lines.append(" · ".join(tag_links))

    lines.append("\n## Days\n")
    for d in days:
        lines.append(f"- [{d['day']}](days/{d['day']}.md) ({d['cnt']} items)")

    lines.append("\n## Navigation\n")
    lines.append("- [Days](days/) — by date")
    lines.append("- [Clusters](clusters/) — thematic groups")
    lines.append("- [Tags](tags/) — by tag")
    lines.append("- [Ideas](ideas/) — all ideas")
    lines.append("- [Publish EN](../publish/en/) — published content")

    path = INDEX_DIR / "INDEX.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_day_index(conn, day: str) -> Path:
    """Build index for a specific day."""
    ensure_index_dirs()

    items = conn.execute("""
        SELECT i.id, i.title, i.url, s.name as source, i.fetched_at
        FROM items i
        JOIN mentions m ON i.id = m.item_id
        JOIN sources s ON i.source_id = s.id
        WHERE m.day = ? ORDER BY i.id
    """, (day,)).fetchall()

    ideas = conn.execute("""
        SELECT id, title, status, viability, created_at
        FROM ideas WHERE created_at LIKE ? ORDER BY id
    """, (f"{day}%",)).fetchall()

    lines = [
        f"# Day: {day}",
        "",
        f"## Items ({len(items)})",
        "",
    ]

    for item in items:
        lines.append(f"- [{item['title']}]({item['url']}) — {item['source']}")

    if ideas:
        lines.append(f"\n## Ideas ({len(ideas)})\n")
        for idea in ideas:
            viability = json.loads(idea["viability"]) if idea["viability"] else {}
            score = viability.get("score", "?")
            lines.append(
                f"- [{idea['title']}](../ideas/idea_{idea['id']}.md) — "
                f"**{score}**/100 — `{idea['status']}`"
            )

    lines.append(f"\n[← Global Index](../INDEX.md)")
    path = INDEX_DIR / "days" / f"{day}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_cluster_index(conn) -> list[Path]:
    """Build index for each cluster."""
    ensure_index_dirs()
    paths = []

    clusters = conn.execute("SELECT id, name FROM clusters ORDER BY name").fetchall()
    for cluster in clusters:
        items = conn.execute("""
            SELECT i.id, i.title, i.url, s.name as source
            FROM items i
            JOIN item_clusters ic ON i.id = ic.item_id
            JOIN sources s ON i.source_id = s.id
            WHERE ic.cluster_id = ?
        """, (cluster["id"],)).fetchall()

        lines = [
            f"# Cluster: {cluster['name']}",
            "",
            f"## Items ({len(items)})\n",
        ]
        for item in items:
            lines.append(f"- [{item['title']}]({item['url']}) — {item['source']}")

        lines.append(f"\n[← Global Index](../INDEX.md)")
        path = INDEX_DIR / "clusters" / f"cluster_{cluster['id']}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)

    return paths


def build_tag_indexes(conn) -> list[Path]:
    """Build index for each tag."""
    ensure_index_dirs()
    paths = []

    tags = conn.execute("""
        SELECT t.id, t.name, COUNT(it.item_id) as cnt
        FROM tags t LEFT JOIN item_tags it ON t.id = it.tag_id
        GROUP BY t.id ORDER BY t.name
    """).fetchall()

    for tag in tags:
        ideas = conn.execute("""
            SELECT i.id, i.title, i.status, i.viability
            FROM ideas i
            JOIN item_tags it ON i.id = it.item_id
            WHERE it.tag_id = ?
        """, (tag["id"],)).fetchall()

        lines = [
            f"# Tag: {tag['name']}",
            "",
            f"## Ideas with this tag ({len(ideas)})\n",
        ]
        for idea in ideas:
            viability = json.loads(idea["viability"]) if idea["viability"] else {}
            score = viability.get("score", "?")
            lines.append(
                f"- [{idea['title']}](../ideas/idea_{idea['id']}.md) — "
                f"**{score}**/100 — `{idea['status']}`"
            )

        lines.append(f"\n[← Global Index](../INDEX.md)")
        path = INDEX_DIR / "tags" / f"tag_{tag['name']}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)

    return paths


def build_idea_indexes(conn) -> list[Path]:
    """Build per-idea INDEX.md (own index for each idea)."""
    ensure_index_dirs()
    paths = []

    ideas = conn.execute("SELECT id, title, status, viability, summary, origin FROM ideas ORDER BY id").fetchall()
    for idea in ideas:
        viability = json.loads(idea["viability"]) if idea["viability"] else {}

        # Related ideas
        related = conn.execute("""
            SELECT i2.id, i2.title, i2.viability
            FROM related_links rl
            JOIN ideas i2 ON rl.to_id = i2.id
            WHERE rl.from_id = ?
            UNION
            SELECT i2.id, i2.title, i2.viability
            FROM related_links rl
            JOIN ideas i2 ON rl.from_id = i2.id
            WHERE rl.to_id = ?
        """, (idea["id"], idea["id"])).fetchall()

        # Specs
        specs = conn.execute(
            "SELECT id, path, status FROM specs WHERE idea_id = ?",
            (idea["id"],)
        ).fetchall()

        # Content bundles
        bundles = conn.execute(
            "SELECT kind, path, status FROM content_bundles WHERE idea_id = ?",
            (idea["id"],)
        ).fetchall()

        # Tags
        tags = conn.execute("""
            SELECT t.name FROM tags t
            JOIN item_tags it ON t.id = it.tag_id
            WHERE it.item_id = ?
        """, (idea["id"],)).fetchall()

        lines = [
            f"# Idea: {idea['title']}",
            "",
            f"**ID**: {idea['id']} · **Status**: {idea['status']} · "
            f"**Score**: {viability.get('score', '?')}/100 · **Origin**: {idea['origin']}",
            "",
        ]

        if idea["summary"]:
            lines.append(f"> {idea['summary']}")
            lines.append("")

        if specs:
            lines.append("## Specs\n")
            for spec in specs:
                spec_path = Path(spec["path"])
                if spec_path.exists():
                    lines.append(
                        f"- [{spec_path.name}]({_rel_link(spec_path, 2)}) — `{spec['status']}`"
                    )
                else:
                    lines.append(f"- {spec_path.name} — `{spec['status']}` (file missing)")
            lines.append("")

        if bundles:
            lines.append("## Content Bundles\n")
            for b in bundles:
                if b["path"]:
                    lines.append(
                        f"- {b['kind']}: {_rel_link(Path(b['path']), 2)} — `{b['status']}`"
                    )
                else:
                    lines.append(f"- {b['kind']}: — — `{b['status']}`")
            lines.append("")

        if tags:
            tag_list = [f"[{t['name']}](../tags/tag_{t['name']}.md)" for t in tags]
            lines.append(f"**Tags**: {' · '.join(tag_list)}\n")

        if related:
            lines.append("## Related Ideas\n")
            for rel in related:
                rv = json.loads(rel["viability"]) if rel["viability"] else {}
                lines.append(
                    f"- [{rel['title']}](idea_{rel['id']}.md) — "
                    f"**{rv.get('score', '?')}**/100"
                )
            lines.append("")

        lines.append("[← Global Index](../INDEX.md)")
        path = INDEX_DIR / "ideas" / f"idea_{idea['id']}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(path)

    return paths


def build_publish_index() -> Path:
    """Build publish/en/INDEX.md for the public site."""
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLISH_DIR / "en").mkdir(parents=True, exist_ok=True)

    ideas_dir = PUBLISH_DIR / "en" / "ideas"
    specs_dir = PUBLISH_DIR / "en" / "specs"

    lines = [
        "# Daily Vibe Coding Ideas and Specs",
        "",
        f"*Updated: {date.today().isoformat()}*",
        "",
        "## Latest Ideas\n",
    ]

    if ideas_dir.exists():
        for md in sorted(ideas_dir.glob("*.md"), reverse=True)[:20]:
            title = md.stem.split("_", 1)[-1].replace("-", " ").title()
            lines.append(f"- [{title}](ideas/{md.name})")

    lines.append("\n## Specs\n")
    if specs_dir.exists():
        for md in sorted(specs_dir.glob("*.md"), reverse=True)[:20]:
            title = md.stem.split("_", 1)[-1].replace("-", " ").title()
            lines.append(f"- [{title}](specs/{md.name})")

    path = PUBLISH_DIR / "en" / "INDEX.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_all_indexes(conn) -> dict:
    """Build all indexes. Returns paths of built files."""
    results = {
        "global": str(build_global_index(conn)),
        "publish": str(build_publish_index()),
        "days": [],
        "clusters": [],
        "tags": [],
        "ideas": [],
    }

    # Day indexes for days with data
    days = conn.execute("SELECT DISTINCT day FROM mentions ORDER BY day DESC LIMIT 30").fetchall()
    for d in days:
        results["days"].append(str(build_day_index(conn, d["day"])))

    # Cluster indexes
    for p in build_cluster_index(conn):
        results["clusters"].append(str(p))

    # Tag indexes
    for p in build_tag_indexes(conn):
        results["tags"].append(str(p))

    # Idea indexes
    for p in build_idea_indexes(conn):
        results["ideas"].append(str(p))

    # Drop index pages for entities that no longer exist in DB
    pruned = 0
    pruned += _prune("clusters", [Path(p) for p in results["clusters"]])
    pruned += _prune("tags", [Path(p) for p in results["tags"]])
    pruned += _prune("ideas", [Path(p) for p in results["ideas"]])
    pruned += _prune_days(conn)
    results["pruned"] = pruned

    return results