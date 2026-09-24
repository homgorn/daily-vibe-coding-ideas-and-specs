"""Единая точка входа движка.

Команды:
  python src/cli.py run            — полный прогон пайплайна
  python src/cli.py add-idea       — ручной ввод идеи (интерактив)
  python src/cli.py build-index    — пересборка MD-индексов
  python src/cli.py dashboard      — регенерация dashboard/data.json
  python src/cli.py status         — статус пайплайна/реестра

Фаза 0: skeleton — init БД, лог прогона, статус из БД.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.config import load_config  # noqa: E402
from engine.store.db import DB_PATH, init_db  # noqa: E402


def cmd_status(args: argparse.Namespace) -> int:
    conn = init_db()
    cfg = load_config()
    counts = {}
    for table in ("items", "ideas", "specs", "news_items", "content_bundles",
                  "run_logs", "publish_ledger", "crawled_pages", "service_docs"):
        counts[table] = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    last_run = conn.execute(
        "SELECT started_at, status, phase FROM run_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()

    print(f"Конфиг: {cfg.get('project', {}).get('name', '?')}")
    print(f"БД: {DB_PATH}")
    print("Таблицы (count):")
    for k, v in counts.items():
        print(f"  {k:16s} {v}")
    if last_run:
        print(f"Последний прогон: {dict(last_run)}")
    else:
        print("Последний прогон: ещё не было")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    conn = init_db()
    phase = "run"
    try:
        cur = conn.execute(
            "INSERT INTO run_logs (started_at, phase) VALUES (datetime('now'), ?)", (phase,)
        )
        run_id = cur.lastrowid
        conn.commit()

        cfg = load_config()
        print(f"[run#{run_id}] Фаза 0: скелет движка, полный пайплайн — Фаза 1")
        print(f"  минимум идей в день: {cfg['engine'].get('min_ideas_per_day')}")

        if cfg.get("knowledge", {}).get("auto_index_on_run", False):
            from engine.knowledge import index_service_docs

            names = index_service_docs(conn)
            print(f"  knowledge: заиндексировано карточек сервисов — {len(names)}")

        conn.execute(
            "UPDATE run_logs SET finished_at = datetime('now'), status = 'ok' WHERE id = ?",
            (run_id,),
        )
        conn.commit()
        return 0
    except Exception as e:  # noqa: BLE001
        conn.execute(
            "UPDATE run_logs SET finished_at = datetime('now'), status = 'failed', details = ? "
            "WHERE id = ?",
            (str(e), cur.lastrowid if "cur" in dir() else -1),
        )
        conn.commit()
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


def cmd_crawl(args: argparse.Namespace) -> int:
    from engine.crawl import crawl_site
    from engine.crawl.robots import RobotsTxt

    conn = init_db()
    if args.robots:
        robots = RobotsTxt.fetch(args.url)
        print(f"robots.txt для {args.url}:")
        print(f"  sitemap: {robots.sitemaps}")
        print(f"  crawl-delay: {robots.crawl_delay()}")
        for sample in ["/", "/docs", "/api"]:
            print(f"  is_allowed({sample}) = {robots.is_allowed(args.url + sample)}")
        return 0

    summary = crawl_site(args.url, max_urls=args.max, verbose=args.verbose)
    print(f"Сайт: {summary['domain']}")
    print(f"  sitemap'ы: {summary['sitemaps'] or 'не объявлены'}")
    print(f"  URL из sitemap: {summary['urls']}")
    print(f"  сохранено в crawled_pages: {summary['stored']}")
    if summary["errors"]:
        print(f"  ошибки ({len(summary['errors'])}):")
        for e in summary["errors"][:5]:
            print(f"    {e}")
    return 0


def cmd_service(args: argparse.Namespace) -> int:
    from engine.knowledge import index_service_docs, list_services, search_services

    if args.action == "index":
        names = index_service_docs()
        print(f"Заиндексировано карточек сервисов: {len(names)}")
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
    print("действия: index | list | search")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily-vibe-engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="полный прогон пайплайна")
    sub.add_parser("add-idea", help="ручной ввод идеи (интерактив, Фаза 1)")
    sub.add_parser("build-index", help="пересборка MD-индексов (Фаза 1)")
    sub.add_parser("dashboard", help="регенерация dashboard/data.json (Фаза 2)")
    sub.add_parser("status", help="статус пайплайна/реестра")

    crawl_p = sub.add_parser("crawl", help="краулинг сайта-референса (robots + sitemap)")
    crawl_p.add_argument("url", help="https://site.com")
    crawl_p.add_argument("--robots", action="store_true", help="только проверить robots.txt")
    crawl_p.add_argument("--max", type=int, default=500, help="макс. URL из sitemap")
    crawl_p.add_argument("--verbose", action="store_true", help="показывать каждый sitemap")

    service_p = sub.add_parser("service", help="карточки сервисов (knowledge/services)")
    service_p.add_argument("action", choices=["index", "list", "search"])
    service_p.add_argument("query", nargs="?", help="для search")

    args = parser.parse_args(argv)

    if args.command == "status":
        return cmd_status(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "crawl":
        return cmd_crawl(args)
    if args.command == "service":
        return cmd_service(args)

    print(f"[{args.command}] ещё не реализована (Фаза 1+)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
