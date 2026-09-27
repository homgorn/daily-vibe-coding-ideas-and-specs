"""
Единая точка входа.

Команды:
  python src/cli.py run            — полный прогон пайплайна
  python src/cli.py add-idea       — ручной ввод идеи (интерактив)
  python src/cli.py build-index    — пересборка MD-индексов
  python src/cli.py validate       — валидация артефактов
  python src/cli.py dashboard      — регенерация dashboard/data.json
  python src/cli.py status         — статусы пайплайна/реестра
  python src/cli.py crawl <url>    — краулинг референс-сайта
  python src/cli.py service index  — индексация knowledge/services/
  python src/cli.py build-site     — статический сайт (GitHub Pages)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    import io

    if isinstance(sys.stdout, io.TextIOWrapper) and (sys.stdout.encoding or "").lower().replace("-", "") not in ("utf8", "utf_8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if isinstance(sys.stderr, io.TextIOWrapper) and (sys.stderr.encoding or "").lower().replace("-", "") not in ("utf8", "utf_8"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine.config import load_config  # noqa: E402
from engine.store.db import DB_PATH, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _rel_path(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return Path(raw).resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return Path(raw).name


def cmd_status(args: argparse.Namespace) -> int:
    conn = init_db()
    cfg = load_config()
    counts = {}
    for table in (
        "items",
        "ideas",
        "specs",
        "clusters",
        "tags",
        "news_items",
        "content_bundles",
        "run_logs",
        "publish_ledger",
        "crawled_pages",
        "service_docs",
    ):
        counts[table] = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    last_run = conn.execute(
        "SELECT started_at, finished_at, status, phase FROM run_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    print(f"Конфиг: {cfg.get('project', {}).get('name', '?')}")
    print(f"БД: {DB_PATH}")
    print("Таблицы (count):")
    for k, v in counts.items():
        print(f"  {k:20s} {v}")
    if last_run:
        print(f"Последний прогон: {dict(last_run)}")
    else:
        print("Последний прогон: ещё не было")
    # Today's stats
    today = date.today().isoformat()
    today_items = conn.execute(
        "SELECT COUNT(*) AS c FROM mentions WHERE day = ?", (today,)
    ).fetchone()["c"]
    today_ideas = conn.execute(
        "SELECT COUNT(*) AS c FROM ideas WHERE created_at LIKE ?", (f"{today}%",)
    ).fetchone()["c"]
    print(f"\nСегодня ({today}): {today_items} items, {today_ideas} ideas")
    # KPI check
    min_items = cfg.get("engine", {}).get("min_items_per_day", 30)
    min_ideas = cfg.get("engine", {}).get("min_ideas_per_day", 5)
    items_ok = "✓" if today_items >= min_items else "✗"
    ideas_ok = "✓" if today_ideas >= min_ideas else "✗"
    print(
        f"KPI: items {items_ok} {today_items}/{min_items}, "
        f"ideas {ideas_ok} {today_ideas}/{min_ideas}"
    )
    return 0


def _close_stale_runs(conn) -> int:
    """Помечает прогоны, оставшиеся в 'running' (убитый процесс), как failed."""
    cur = conn.execute(
        "UPDATE run_logs SET finished_at = datetime('now'), status = 'failed', "
        "details = COALESCE(details, '') || 'stale: process did not finish' "
        "WHERE status = 'running' AND finished_at IS NULL"
    )
    conn.commit()
    return cur.rowcount


def cmd_run(args: argparse.Namespace) -> int:
    conn = init_db()
    phase = "fetch"
    run_start = time.time()
    stale = _close_stale_runs(conn)
    if stale:
        print(f"  закрыто висящих прогонов: {stale}")
    try:
        cur = conn.execute(
            "INSERT INTO run_logs (started_at, phase) VALUES (datetime('now'), ?)",
            (phase,),
        )
        run_id = cur.lastrowid
        conn.commit()
        cfg = load_config()
        print(f"[run#{run_id}] Full pipeline — {date.today().isoformat()}")
        print(
            f"  min_items: {cfg['engine'].get('min_items_per_day')}, "
            f"min_ideas: {cfg['engine'].get('min_ideas_per_day')}"
        )
        results = {}
        # Phase 1: FETCH
        print("\n[1/8] FETCH...")
        from engine.fetch import fetch_all

        fetch_results = fetch_all(cfg)
        total_fetched = sum(fetch_results.values())
        results["fetch"] = fetch_results
        print(f"  {fetch_results} = {total_fetched} new items")
        # Phase 2: NEWS
        print("\n[2/8] NEWS...")
        from engine.news import run_news

        news_results = run_news(cfg)
        results["news"] = news_results
        print(
            f"  fetched={news_results['fetched']}, stored={news_results['stored']}, "
            f"analyzed={news_results['analyzed']}"
        )
        # Phase 3: INGEST
        print("\n[3/8] INGEST...")
        from engine.ingest import process_inbox

        ingest_results = process_inbox(conn)
        results["ingest"] = ingest_results
        print(
            f"  inbox={ingest_results['inbox']}, candidates={ingest_results['candidates']}, "
            f"manual={ingest_results['manual']}, new={ingest_results['new']}"
        )
        # Phase 4: SYNTHESIZE
        print("\n[4/8] SYNTHESIZE...")
        from engine.providers import get_provider
        from engine.synthesize import run_synthesis

        registry = get_provider(cfg)
        registry.start_budget("synthesize")
        synth_results = run_synthesis(cfg)
        results["synthesize"] = synth_results
        if "error" in synth_results:
            print(f"  skipped: {synth_results['error']}")
        else:
            print(
                f"  clusters={synth_results['clusters']}, ideas={synth_results['ideas']}"
            )
        # Phase 5: SPEC
        print("\n[5/8] SPEC...")
        from engine.spec import run_spec_generation

        registry.start_budget("spec")
        spec_results = run_spec_generation(cfg)
        results["spec"] = spec_results
        print(f"  specs generated: {spec_results['specs']}")
        spent = registry.budget_report()
        if spent:
            results["llm_budget_minutes"] = spent
            print(f"  LLM time spent (min): {spent}")
        # Phase 6: VALIDATE
        print("\n[6/8] VALIDATE...")
        from engine.validate import validate_artifact
        from engine.store import PUBLISH_DIR

        validated = 0
        failed = 0
        specs_dir = PUBLISH_DIR / "en" / "specs"
        if specs_dir.exists():
            for md_file in sorted(specs_dir.glob("*.md")):
                report = validate_artifact(md_file, "spec", check_links_online=False)
                if report.passed:
                    validated += 1
                else:
                    failed += 1
                    errors = []
                    for r in report.results:
                        errors.extend(r.errors)
                    print(f"  FAIL {md_file.name}: {errors[:3]}")
        results["validate"] = {"passed": validated, "failed": failed}
        print(f"  validated={validated}, failed={failed}")
        # Phase 7: INDEX
        print("\n[7/8] INDEX...")
        from engine.index import build_all_indexes

        index_results = build_all_indexes(conn)
        results["index"] = index_results
        total_indexed = (
            len(index_results["days"])
            + len(index_results["clusters"])
            + len(index_results["tags"])
            + len(index_results["ideas"])
        )
        print(
            f"  global={index_results['global']}, publish={index_results['publish']}, "
            f"sub-indexes={total_indexed}"
        )
        # Knowledge auto-index
        if cfg.get("knowledge", {}).get("auto_index_on_run", False):
            from engine.knowledge import index_service_docs

            names = index_service_docs(conn)
            results["knowledge"] = len(names)
            print(f"  knowledge: {len(names)} service cards indexed")
        # Phase 8: SITE
        print("\n[8/8] SITE...")
        from engine.publish.site import build_site

        site_stats = build_site()
        results["site"] = {
            "pages": site_stats["pages"],
            "broken_links": len(site_stats["broken_links"]),
            "excluded": site_stats.get("excluded", 0),
        }
        print(
            f"  pages={site_stats['pages']}, "
            f"broken links={len(site_stats['broken_links'])}, "
            f"excluded unvalidated={site_stats.get('excluded', 0)}"
        )
        # Update run log
        elapsed = time.time() - run_start
        conn.execute(
            "UPDATE run_logs SET finished_at=datetime('now'), status='ok', details=? WHERE id=?",
            (json.dumps(results, ensure_ascii=False), run_id),
        )
        conn.commit()
        # Summary
        print(f"\n{'='*50}")
        print(f"RUN #{run_id} COMPLETE in {elapsed:.1f}s")
        print(f"  items fetched: {total_fetched}")
        print(f"  ideas: {synth_results.get('ideas', 0)}")
        print(f"  specs: {spec_results.get('specs', 0)}")
        print(f"  validation: {validated} passed, {failed} failed")
        print(f"  indexes: {total_indexed} built")
        print(
            f"  site pages: {site_stats['pages']}, "
            f"broken links: {len(site_stats['broken_links'])}"
        )
        # KPI check
        min_items = cfg.get("engine", {}).get("min_items_per_day", 30)
        min_ideas = cfg.get("engine", {}).get("min_ideas_per_day", 5)
        if total_fetched < min_items:
            print(f"  WARNING: {total_fetched} < {min_items} min items")
        if synth_results.get("ideas", 0) < min_ideas:
            print(
                f"  WARNING: {synth_results.get('ideas', 0)} < {min_ideas} min ideas"
            )
        return 0
    except Exception as e:
        import traceback

        traceback.print_exc()
        conn.execute(
            "UPDATE run_logs SET finished_at=datetime('now'), status='failed', details=? WHERE id=?",
            (str(e), run_id if "run_id" in dir() else -1),
        )
        conn.commit()
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_build_index(args: argparse.Namespace) -> int:
    conn = init_db()
    from engine.index import build_all_indexes

    results = build_all_indexes(conn)
    print(f"Global: {results['global']}")
    print(f"Publish: {results['publish']}")
    print(
        f"Days: {len(results['days'])}, Clusters: {len(results['clusters'])}, "
        f"Tags: {len(results['tags'])}, Ideas: {len(results['ideas'])}"
    )
    return 0


def cmd_add_idea(args: argparse.Namespace) -> int:
    conn = init_db()
    from engine.ingest import add_idea_interactive

    result = add_idea_interactive(conn)
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from engine.validate import validate_artifact, validate_all

    if args.path:
        report = validate_artifact(args.path, args.type, check_links_online=args.links)
        print(f"Artifact: {report.artifact_path}")
        print(f"Passed: {report.passed}")
        for r in report.results:
            status = "✓" if r.passed else "✗"
            print(f"  {status} {r.agent}: score={r.score:.1f}")
            for e in r.errors:
                print(f"    ERROR: {e}")
            for w in r.warnings:
                print(f"    WARN: {w}")
        return 0 if report.passed else 1
    elif args.dir:
        reports = validate_all(args.dir, args.type, check_links_online=args.links)
        passed = sum(1 for r in reports if r.passed)
        print(
            f"Validated {len(reports)} artifacts: {passed} passed, "
            f"{len(reports) - passed} failed"
        )
        for r in reports:
            if not r.passed:
                print(f"  FAIL: {r.artifact_path}")
        return 0 if passed == len(reports) else 1
    else:
        print("Provide --path FILE or --dir DIR")
        return 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    conn = init_db()
    today = date.today().isoformat()
    # Gather dashboard data
    data = {
        "date": today,
        "counts": {},
        "recent_ideas": [],
        "recent_specs": [],
        "recent_items": [],
        "clusters": [],
        "tags": [],
        "last_run": None,
    }
    for table in (
        "items",
        "ideas",
        "specs",
        "clusters",
        "tags",
        "publish_ledger",
    ):
        data["counts"][table] = conn.execute(
            f"SELECT COUNT(*) AS c FROM {table}"
        ).fetchone()["c"]
    # Today's items
    data["counts"]["today_items"] = conn.execute(
        "SELECT COUNT(*) AS c FROM mentions WHERE day = ?", (today,)
    ).fetchone()["c"]
    # Today's ideas
    data["counts"]["today_ideas"] = conn.execute(
        "SELECT COUNT(*) AS c FROM ideas WHERE created_at LIKE ?", (f"{today}%",)
    ).fetchone()["c"]
    # Recent ideas
    rows = conn.execute(
        """
        SELECT id, title, summary, status, viability, origin, created_at
        FROM ideas ORDER BY created_at DESC LIMIT 20
    """
    ).fetchall()
    for r in rows:
        v = json.loads(r["viability"]) if r["viability"] else {}
        data["recent_ideas"].append(
            {
                "id": r["id"],
                "title": r["title"],
                "summary": r["summary"],
                "status": r["status"],
                "score": v.get("score", 0),
                "origin": r["origin"],
                "date": r["created_at"][:10],
            }
        )
    # Recent specs
    rows = conn.execute(
        """
        SELECT s.id, s.path, s.status, s.created_at, i.title as idea_title
        FROM specs s JOIN ideas i ON s.idea_id = i.id
        ORDER BY s.created_at DESC LIMIT 10
    """
    ).fetchall()
    for r in rows:
        data["recent_specs"].append(
            {
                "id": r["id"],
                "path": _rel_path(r["path"]),
                "status": r["status"],
                "idea_title": r["idea_title"],
                "date": r["created_at"][:10],
            }
        )
    # Clusters
    rows = conn.execute(
        """
        SELECT c.id, c.name, COUNT(ic.item_id) as cnt
        FROM clusters c LEFT JOIN item_clusters ic ON c.id = ic.cluster_id
        GROUP BY c.id ORDER BY cnt DESC LIMIT 15
    """
    ).fetchall()
    for r in rows:
        data["clusters"].append({"id": r["id"], "name": r["name"], "count": r["cnt"]})
    # Tags
    rows = conn.execute(
        """
        SELECT t.name, COUNT(it.item_id) as cnt
        FROM tags t LEFT JOIN item_tags it ON t.id = it.tag_id
        GROUP BY t.id ORDER BY cnt DESC LIMIT 30
    """
    ).fetchall()
    for r in rows:
        data["tags"].append({"name": r["name"], "count": r["cnt"]})
    # Last run
    last = conn.execute(
        "SELECT started_at, finished_at, status, phase FROM run_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if last:
        data["last_run"] = dict(last)
    # Write to dashboard/data.json
    dashboard_path = ROOT / "dashboard" / "data.json"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Dashboard data written: {dashboard_path}")
    print(
        f"  ideas={data['counts']['ideas']}, specs={data['counts']['specs']}, "
        f"today_items={data['counts']['today_items']}, "
        f"today_ideas={data['counts']['today_ideas']}"
    )
    return 0


def cmd_crawl(args: argparse.Namespace) -> int:
    from engine.crawl import crawl_site
    from engine.crawl.robots import RobotsTxt

    init_db()
    if args.robots:
        robots = RobotsTxt.fetch(args.url)
        print(f"robots.txt for {args.url}:")
        print(f"  sitemaps: {robots.sitemaps}")
        print(f"  crawl-delay: {robots.crawl_delay()}")
        for sample in ["/", "/docs", "/api"]:
            print(f"  is_allowed({sample}) = {robots.is_allowed(args.url + sample)}")
        return 0
    summary = crawl_site(args.url, max_urls=args.max, verbose=args.verbose)
    print(f"Site: {summary['domain']}")
    print(f"  sitemaps: {summary['sitemaps'] or 'none declared'}")
    print(f"  URLs from sitemap: {summary['urls']}")
    print(f"  stored in crawled_pages: {summary['stored']}")
    if summary["errors"]:
        print(f"  errors ({len(summary['errors'])}):")
        for e in summary["errors"][:5]:
            print(f"    {e}")
    return 0


def cmd_service(args: argparse.Namespace) -> int:
    from engine.knowledge import index_service_docs, list_services, search_services

    if args.action == "index":
        names = index_service_docs()
        print(f"Indexed service cards: {len(names)}")
        for n in names:
            print(f"  - {n}")
        return 0
    if args.action == "list":
        for s in list_services():
            print(f"  {s['name']:24s} {s['kind']:8s} {s['docs_path']}")
        return 0
    if args.action == "search":
        for s in search_services(args.query):
            print(f"  {s['name']:24s} {s['docs_url'] or ''}")
        return 0
    print("actions: index | list | search")
    return 1


def cmd_build_site(args: argparse.Namespace) -> int:
    from engine.publish.site import build_site

    out = Path(args.out) if getattr(args, "out", None) else None
    stats = build_site(out_dir=out)
    print(f"Site built: {stats['out']}")
    print(
        f"  pages={stats['pages']}, ideas={stats['ideas']}, specs={stats['specs']}, "
        f"dashboard={'yes' if stats['dashboard'] else 'no'}"
    )
    if stats["broken_links"]:
        print(f"  BROKEN LINKS ({len(stats['broken_links'])}):")
        for bl in stats["broken_links"][:10]:
            print(f"    {bl}")
        return 1
    print("  broken links: 0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily-vibe-engine")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="full pipeline run")
    sub.add_parser("add-idea", help="interactive manual idea entry")
    sub.add_parser("build-index", help="rebuild all MD indexes")
    sub.add_parser("dashboard", help="regenerate dashboard/data.json")
    sub.add_parser("status", help="pipeline/ledger status summary")
    site_p = sub.add_parser("build-site", help="build static HTML site (GitHub Pages)")
    site_p.add_argument("--out", help="output dir (default: site/)")
    val_p = sub.add_parser("validate", help="validate artifacts")
    val_p.add_argument("--path", help="validate single file")
    val_p.add_argument("--dir", help="validate all .md in directory")
    val_p.add_argument("--type", default="idea", help="artifact type")
    val_p.add_argument("--links", action="store_true", help="check links online")
    crawl_p = sub.add_parser("crawl", help="crawl reference site")
    crawl_p.add_argument("url", help="https://site.com")
    crawl_p.add_argument("--robots", action="store_true", help="only check robots.txt")
    crawl_p.add_argument("--max", type=int, default=500, help="max URLs")
    crawl_p.add_argument("--verbose", action="store_true")
    service_p = sub.add_parser("service", help="service cards")
    service_p.add_argument("action", choices=["index", "list", "search"])
    service_p.add_argument("query", nargs="?", help="for search")
    args = parser.parse_args(argv)
    handlers = {
        "status": cmd_status,
        "run": cmd_run,
        "crawl": cmd_crawl,
        "service": cmd_service,
        "build-index": cmd_build_index,
        "build-site": cmd_build_site,
        "add-idea": cmd_add_idea,
        "validate": cmd_validate,
        "dashboard": cmd_dashboard,
    }
    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    print(f"[{args.command}] not implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
