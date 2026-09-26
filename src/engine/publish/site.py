"""Static site builder for GitHub Pages / Cloudflare Pages.

Reads publish/{lang}/*.md (ideas, specs), renders HTML pages with SEO meta
(canonical, OG, JSON-LD), listing pages, RSS, sitemap.xml, robots.txt, 404,
dashboard copy. All internal links are relative — works on any domain or
sub-path (project pages). Output: site/ (gitignored; CI builds & deploys).
"""

from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown as md_lib

ROOT = Path(__file__).resolve().parents[3]
SITE_DIR = ROOT / "site"

_MD = md_lib.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if key:
            meta[key] = _scalar(val)
    return meta, text[m.end():]


def _scalar(val: str):
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if re.fullmatch(r"-?\d+\.\d+", val):
        return float(val)
    return val


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:max_len].strip("-")


def md_to_html(text: str) -> str:
    _MD.reset()
    return _MD.convert(text)


def _page(
    site: dict,
    *,
    title: str,
    description: str,
    canonical_path: str,
    body: str,
    rel: str = "",
    jsonld: dict | None = None,
    og_type: str = "website",
    extra_head: str = "",
) -> str:
    base = site["base_url"].rstrip("/")
    canonical = f"{base}/{canonical_path.lstrip('/')}" if base else canonical_path
    full_title = html.escape(site["title"] if title == site["title"] else f"{title} | {site['title']}")
    desc = html.escape(description[:300])
    jsonld_html = ""
    if jsonld:
        jsonld_html = (
            '\n  <script type="application/ld+json">'
            + json.dumps(jsonld, ensure_ascii=False)
            + "</script>"
        )
    return f"""<!doctype html>
<html lang="{site['language']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{full_title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(site['title'])}" href="{rel}rss.xml">
  <link rel="stylesheet" href="{rel}assets/style.css">{jsonld_html}{extra_head}
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{rel}index.html">{html.escape(site['title'])}</a>
    <nav>
      <a href="{rel}ideas/index.html">Ideas</a>
      <a href="{rel}specs/index.html">Specs</a>
      <a href="{rel}dashboard/index.html">Dashboard</a>
      <a href="{rel}rss.xml">RSS</a>
    </nav>
  </header>
  <main>
{body}
  </main>
  <footer class="site-footer">
    <p>{html.escape(site['tagline'])}</p>
    <p>Content: <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND 4.0</a> ·
       Built by Daily Vibe Engine · <a href="{site['github_url']}">GitHub</a></p>
  </footer>
</body>
</html>
"""


def _meta_line(meta: dict) -> str:
    parts = []
    if meta.get("date"):
        parts.append(str(meta["date"]))
    if meta.get("viability_score") is not None:
        parts.append(f"viability {meta['viability_score']}/100")
    if meta.get("status"):
        parts.append(f"status: {meta['status']}")
    tags = meta.get("tags") or []
    if tags:
        parts.append("tags: " + ", ".join(str(t) for t in tags))
    return " · ".join(parts)


def _listing(entries: list[dict], kind: str, rel: str) -> str:
    rows = []
    for e in entries:
        score = e["meta"].get("viability_score")
        badge = f'<span class="badge">{score}</span>' if score is not None else ""
        desc = html.escape((e["meta"].get("description") or e["meta"].get("summary") or "")[:220])
        rows.append(
            f'    <li class="card"><a class="card-link" href="{rel}{e["href"]}">'
            f"<h2>{html.escape(e['title'])}</h2></a>"
            f'<p class="muted">{_meta_line(e["meta"])}</p>'
            f"<p>{desc}</p>{badge}</li>"
        )
    if not rows:
        rows.append("    <li class=\"card muted\">Nothing published yet — run the engine.</li>")
    return (
        f'    <h1>{"Ideas" if kind == "idea" else "Specs"}</h1>\n'
        f'    <ul class="cards">\n' + "\n".join(rows) + "\n    </ul>"
    )


def _article(entry: dict, kind: str, rel: str, site: dict) -> str:
    meta = entry["meta"]
    crumb_kind = "Ideas" if kind == "idea" else "Specs"
    crumb_href = "index.html"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article" if kind == "idea" else "TechArticle",
        "headline": entry["title"],
        "description": meta.get("description", ""),
        "datePublished": str(meta.get("date", "")),
        "url": f"{site['base_url'].rstrip('/')}/{entry['path']}",
        "isPartOf": {"@type": "WebSite", "name": site["title"], "url": site["base_url"]},
    }
    if meta.get("tags"):
        jsonld["keywords"] = ", ".join(str(t) for t in meta["tags"])
    meta_line = _meta_line(meta)
    body = f"""    <nav class="crumbs"><a href="../index.html">Home</a> / <a href="{crumb_href}">{crumb_kind}</a> / {html.escape(entry['title'][:60])}</nav>
    <article>
      <header>
        <h1>{html.escape(entry['title'])}</h1>
        <p class="muted">{html.escape(meta_line)}</p>
      </header>
      <div class="content">
{entry['html']}
      </div>
    </article>
    <p class="back"><a href="{crumb_href}">← All {crumb_kind}</a></p>"""
    return _page(
        site,
        title=entry["title"],
        description=meta.get("description", "") or entry["title"],
        canonical_path=entry["path"],
        body=body,
        rel=rel,
        jsonld=jsonld,
        og_type="article",
    )


def _load_entries(source_dir: Path, kind: str) -> list[dict]:
    entries = []
    d = source_dir / kind
    if not d.exists():
        return entries
    for md_file in sorted(d.glob("*.md")):
        meta, body = parse_frontmatter(md_file.read_text(encoding="utf-8"))
        idea_id = str(meta.get("idea_id") or "")
        stem = md_file.stem
        m = re.match(r"^(\d+)_", stem)
        numeric_id = idea_id or (m.group(1) if m else "")
        prefix = "idea" if kind == "ideas" else "spec"
        slug = slugify(str(meta.get("title") or stem))
        fname = f"{prefix}-{numeric_id}-{slug}.html" if slug else f"{prefix}-{numeric_id or 'x'}.html"
        title = str(meta.get("title") or stem)
        desc = str(meta.get("description") or "") or re.sub(r"\s+", " ", re.sub(r"[#>*`\-\[\]|]", "", body))[:200]
        entries.append({
            "file": md_file,
            "meta": meta,
            "title": title,
            "description": desc[:300],
            "body": body,
            "html": md_to_html(body),
            "href": f"{kind}/{fname}",
            "path": f"{kind}/{fname}",
            "date": str(meta.get("date") or ""),
            "id": int(numeric_id) if str(numeric_id).isdigit() else 0,
        })
    entries.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return entries


def _rss(site: dict, entries: list[dict], limit: int) -> str:
    base = site["base_url"].rstrip("/")
    items = []
    for e in entries[:limit]:
        link = f"{base}/{e['path']}"
        try:
            dt = datetime.strptime(e["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            pub = format_datetime(dt)
        except (ValueError, TypeError):
            pub = format_datetime(datetime.now(timezone.utc))
        desc = html.escape(e["description"])
        items.append(
            f"    <item>\n"
            f"      <title>{html.escape(e['title'])}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid isPermaLink=\"true\">{link}</guid>\n"
            f"      <pubDate>{pub}</pubDate>\n"
            f"      <description>{desc}</description>\n"
            f"    </item>"
        )
    now = format_datetime(datetime.now(timezone.utc))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{html.escape(site['title'])}</title>\n"
        f"    <link>{base}/</link>\n"
        f"    <description>{html.escape(site['tagline'])}</description>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        f"    <language>{site['language']}</language>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )


def _sitemap(site: dict, paths: list[str], dates: dict[str, str]) -> str:
    base = site["base_url"].rstrip("/")
    urls = []
    for p in paths:
        loc = f"{base}/{p.lstrip('/')}"
        last = dates.get(p, "")
        lastmod = f"\n    <lastmod>{last}</lastmod>" if last else ""
        urls.append(f"  <url>\n    <loc>{loc}</loc>{lastmod}\n  </url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


STYLE_CSS = """\
:root { --bg:#0f1115; --card:#161a22; --border:#262d3a; --fg:#e6e6e6; --muted:#8a93a3; --accent:#5ea1ff; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background:var(--bg); color:var(--fg); line-height:1.6; }
main { max-width: 860px; margin: 0 auto; padding: 24px 20px 60px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.site-header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
  padding:16px 20px; border-bottom:1px solid var(--border); background:var(--card); }
.brand { font-weight:700; color:var(--fg); font-size:16px; }
.site-header nav a { margin-left:16px; color:var(--muted); }
.site-header nav a:hover { color:var(--fg); }
.site-footer { border-top:1px solid var(--border); padding:20px; text-align:center; color:var(--muted); font-size:13px; }
.muted { color: var(--muted); }
.cards { list-style:none; padding:0; margin:0; display:grid; gap:14px; }
.card { position:relative; background:var(--card); border:1px solid var(--border); border-radius:10px; padding:16px 18px; }
.card h2 { margin:0 0 6px; font-size:18px; }
.card-link { color:var(--fg); }
.card-link:hover { color:var(--accent); text-decoration:none; }
.badge { position:absolute; top:14px; right:16px; background:#1f2937; border:1px solid var(--border);
  border-radius:999px; padding:2px 10px; font-size:13px; color:var(--accent); }
.hero { padding: 28px 0 8px; }
.hero h1 { margin:0 0 8px; font-size:30px; }
.stats { display:flex; gap:20px; flex-wrap:wrap; margin:18px 0 26px; }
.stat { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 18px; min-width:120px; }
.stat b { display:block; font-size:26px; }
.stat span { color:var(--muted); font-size:13px; }
h1 { font-size:26px; } h2 { font-size:20px; }
article header h1 { font-size:28px; margin-bottom:4px; }
.content pre { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:12px; overflow-x:auto; }
.content code { background:var(--card); padding:1px 5px; border-radius:4px; font-size:14px; }
.content pre code { background:none; padding:0; }
.content table { border-collapse:collapse; width:100%; margin:12px 0; }
.content th, .content td { border:1px solid var(--border); padding:8px 10px; text-align:left; }
.content th { background:var(--card); }
.content blockquote { border-left:3px solid var(--accent); margin:12px 0; padding:4px 16px; color:var(--muted); }
.crumbs { color:var(--muted); font-size:14px; margin-bottom:14px; }
.back { margin-top:28px; }
.section-title { margin:30px 0 12px; border-bottom:1px solid var(--border); padding-bottom:6px; }
"""


def _check_internal_links(out_dir: Path) -> list[str]:
    broken = []
    for p in out_dir.rglob("*.html"):
        text = p.read_text(encoding="utf-8", errors="replace")
        for href in re.findall(r'(?:href|src)="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target_str = href.split("#", 1)[0].split("?", 1)[0]
            if not target_str:
                continue
            target = (p.parent / target_str).resolve()
            if not target.exists():
                broken.append(f"{p.relative_to(out_dir)} -> {href}")
    return broken


_ABS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _sanitize_public_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return

    def clean(node):
        if isinstance(node, dict):
            return {k: clean(v) for k, v in node.items()}
        if isinstance(node, list):
            return [clean(v) for v in node]
        if isinstance(node, str) and _ABS_PATH.match(node):
            return node.replace("\\", "/").rsplit("/", 1)[-1]
        return node

    path.write_text(
        json.dumps(clean(data), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_site(config: dict | None = None, source_dir: Path | None = None,
               out_dir: Path | None = None) -> dict:
    if config is None:
        from engine.config import load_config
        config = load_config()
    site_cfg = config.get("site", {})
    site = {
        "base_url": site_cfg.get("base_url", "https://example.com").rstrip("/"),
        "title": site_cfg.get("title", "Daily Vibe Coding Ideas & Specs"),
        "tagline": site_cfg.get("tagline", ""),
        "language": site_cfg.get("language", "en"),
        "github_url": site_cfg.get("github_url", ""),
        "items_per_feed": int(site_cfg.get("items_per_feed", 20)),
    }

    if source_dir is None:
        import engine.store as store
        source_dir = Path(store.PUBLISH_DIR) / "en"
    if out_dir is None:
        out_dir = Path(SITE_DIR)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sub in ("", "ideas", "specs", "assets", "dashboard"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    ideas = _load_entries(source_dir, "ideas")
    specs = _load_entries(source_dir, "specs")
    all_entries = ideas + specs

    # Article pages
    for e in ideas:
        (out_dir / e["href"]).write_text(
            _article(e, "idea", "../", site), encoding="utf-8")
    for e in specs:
        (out_dir / e["href"]).write_text(
            _article(e, "spec", "../", site), encoding="utf-8")

    # Listing pages (inside kind dir, so hrefs are relative to it)
    ideas_body = _listing([{**e, "href": e["href"].split("/", 1)[-1]} for e in ideas], "idea", "")
    (out_dir / "ideas" / "index.html").write_text(
        _page(site, title="Ideas", description="Latest researched product ideas with viability scores.",
              canonical_path="ideas/index.html", body=ideas_body, rel="../"), encoding="utf-8")
    specs_body = _listing([{**e, "href": e["href"].split("/", 1)[-1]} for e in specs], "spec", "")
    (out_dir / "specs" / "index.html").write_text(
        _page(site, title="Specs", description="Agent-ready product specs (Spec Kit + BMAD hybrid).",
              canonical_path="specs/index.html", body=specs_body, rel="../"), encoding="utf-8")

    # KPI from DB (best-effort)
    kpi = {"items_today": 0, "ideas": len(ideas), "specs": len(specs)}
    try:
        from datetime import date as _date
        from engine.store.db import init_db
        conn = init_db()
        kpi["items_today"] = conn.execute(
            "SELECT COUNT(*) FROM mentions WHERE day = ?", (_date.today().isoformat(),)
        ).fetchone()[0]
        kpi["ideas"] = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        kpi["specs"] = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
    except Exception:  # noqa: BLE001
        pass

    latest_ideas = _listing(ideas[:10], "idea", "")
    latest_specs = _listing(specs[:10], "spec", "")
    landing = f"""    <section class="hero">
      <h1>{html.escape(site['title'])}</h1>
      <p class="muted">{html.escape(site['tagline'])}</p>
    </section>
    <div class="stats">
      <div class="stat"><b>{kpi['items_today']}</b><span>items today</span></div>
      <div class="stat"><b>{kpi['ideas']}</b><span>ideas total</span></div>
      <div class="stat"><b>{kpi['specs']}</b><span>specs total</span></div>
    </div>
    <h2 class="section-title">Latest ideas</h2>
    <ul class="cards">
{latest_ideas}
    </ul>
    <h2 class="section-title">Latest specs</h2>
    <ul class="cards">
{latest_specs}
    </ul>
"""
    landing_jsonld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site["title"],
        "description": site["tagline"],
        "url": site["base_url"] + "/",
    }
    (out_dir / "index.html").write_text(
        _page(site, title=site["title"], description=site["tagline"],
              canonical_path="index.html", body=landing, jsonld=landing_jsonld),
        encoding="utf-8")

    # 404
    not_found = """    <h1>404 — not found</h1>
    <p class="muted">This page does not exist.</p>
    <p><a href="index.html">← Back home</a></p>"""
    (out_dir / "404.html").write_text(
        _page(site, title="404", description="Page not found",
              canonical_path="404.html", body=not_found), encoding="utf-8")

    # RSS / sitemap / robots / .nojekyll
    (out_dir / "rss.xml").write_text(_rss(site, all_entries, site["items_per_feed"]), encoding="utf-8")
    dates = {e["path"]: e["date"] for e in all_entries}
    paths = ["index.html", "ideas/index.html", "specs/index.html"] + [e["path"] for e in all_entries]
    (out_dir / "sitemap.xml").write_text(_sitemap(site, paths, dates), encoding="utf-8")
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site['base_url']}/sitemap.xml\n", encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    # CSS
    (out_dir / "assets" / "style.css").write_text(STYLE_CSS, encoding="utf-8")

    # Dashboard
    dash_src = ROOT / "dashboard"
    copied_dash = False
    if (dash_src / "index.html").exists():
        shutil.copy2(dash_src / "index.html", out_dir / "dashboard" / "index.html")
        if (dash_src / "data.json").exists():
            shutil.copy2(dash_src / "data.json", out_dir / "dashboard" / "data.json")
            _sanitize_public_json(out_dir / "dashboard" / "data.json")
        copied_dash = True

    broken = _check_internal_links(out_dir)
    pages = len(list(out_dir.rglob("*.html")))
    return {
        "out": str(out_dir),
        "pages": pages,
        "ideas": len(ideas),
        "specs": len(specs),
        "rss": True,
        "sitemap": True,
        "dashboard": copied_dash,
        "broken_links": broken,
        "kpi": kpi,
    }
