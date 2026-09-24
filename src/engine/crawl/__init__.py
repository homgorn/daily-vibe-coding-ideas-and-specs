"""Модуль crawl: честный краулинг сайтов-референсов.

Возможности:
- robots.txt: парсер + проверка is_allowed (RFC 9309) + Crawl-delay + Sitemap-подсказки
- sitemap: парсер XML/gz, sitemapindex с одним уровнем рекурсии
- реестр crawled_pages в БД: что скачали, когда, разрешено ли robots

Используется для: референсы идей, материалы для спеков, документации сервисов.
Фаза 1: парсеры готовы; сетевые прогоны — по команде `python src/cli.py crawl`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.crawl.robots import RobotsTxt  # noqa: E402
from engine.crawl.sitemap import fetch_sitemap, parse_sitemap  # noqa: E402
from engine.store.db import init_db  # noqa: E402

__all__ = ["RobotsTxt", "fetch_sitemap", "parse_sitemap"]


def crawl_site(
    base_url: str,
    user_agent: str = "*",
    max_urls: int = 500,
    timeout: int = 15,
    verbose: bool = False,
) -> dict:
    """Полный цикл: robots.txt → sitemap → запись URL в crawled_pages.

    Возвращает сводку: {domain, allowed, sitemaps, urls, errors, stored}.
    """
    conn = init_db()
    robots = RobotsTxt.fetch(base_url, timeout=timeout)
    domain = base_url.replace("https://", "").replace("http://", "").split("/")[0]

    sitemap_candidates = list(robots.sitemaps[:5])
    if not sitemap_candidates:
        for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml", "/sitemaps.xml"):
            candidate = base_url.rstrip("/") + path
            if robots.is_allowed(candidate, user_agent):
                sitemap_candidates.append(candidate)

    urls_all: list[str] = []
    errors: list[str] = []
    for sitemap_url in sitemap_candidates[:5]:
        if verbose:
            print(f"  sitemap: {sitemap_url}")
        urls, errs = fetch_sitemap(sitemap_url, timeout=timeout, max_urls=max_urls)
        for u in urls:
            if robots.is_allowed(u, user_agent):
                urls_all.append(u)
        errors.extend(errs)

    delay = robots.crawl_delay(user_agent)
    stored = 0
    for url in urls_all[:max_urls]:
        if not robots.is_allowed(url, user_agent):
            continue
        stored += _store_page(conn, url, domain, allowed=True)
        if delay:
            time.sleep(min(delay, 5))

    return {
        "domain": domain,
        "allowed": True,
        "sitemaps": sitemap_candidates,
        "urls": len(urls_all),
        "errors": errors,
        "stored": stored,
    }


def _store_page(conn, url: str, domain: str, allowed: bool) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO crawled_pages (url, domain, robots_allowed, crawled_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (url, domain, int(allowed)),
    )
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0]