"""Парсер sitemap (XML + gzip + sitemapindex).

Поддерживает: urlset (url/loc), sitemapindex (sitemap/loc, один уровень рекурсии),
gzip-сжатие (magic bytes 1f 8b). Только stdlib.
"""

from __future__ import annotations

import gzip
import io
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _is_gzip(data: bytes) -> bool:
    return data[:2] == b"\x1f\x8b"


def _decompress(data: bytes) -> bytes:
    if _is_gzip(data):
        return gzip.GzipFile(fileobj=io.BytesIO(data)).read()
    return data


def parse_sitemap(content: bytes, max_urls: int = 5000) -> list[str]:
    """Возвращает список URL из содержимого sitemap (urlset или sitemapindex)."""
    data = _decompress(content)
    root = ET.fromstring(data)
    urls: list[str] = []
    for loc in root.findall(".//sm:loc", NS):
        url = (loc.text or "").strip()
        if url:
            urls.append(url)
    return urls[:max_urls]


def parse_sitemap_with_index(
    content: bytes, base_url: str = "", max_urls: int = 5000
) -> tuple[list[str], list[str]]:
    """(urls, child_sitemaps) — child_sitemaps для одного уровня рекурсии."""
    data = _decompress(content)
    root = ET.fromstring(data)
    urls: list[str] = []
    children: list[str] = []
    for loc in root.findall(".//sm:loc", NS):
        url = (loc.text or "").strip()
        if not url:
            continue
        if url.endswith(".gz") or url.endswith(".xml") or "/sitemap" in url:
            children.append(url)
        else:
            urls.append(url)
    return urls[:max_urls], children


def fetch_sitemap(
    url: str,
    timeout: int = 15,
    max_urls: int = 5000,
    user_agent: str = "DailyVibeEngine/0.1",
) -> tuple[list[str], list[str]]:
    """Скачивает sitemap (или sitemapindex + 1 уровень детей), возвращает (urls, errors).

    Ошибки отдельных детей не роняют общий результат — они в errors.
    """
    from engine.crawl.net import ssl_context

    urls: list[str] = []
    errors: list[str] = []

    def _get(u: str) -> bytes | None:
        req = urllib.request.Request(u, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError, ET.ParseError) as e:
            errors.append(f"{u}: {e}")
            return None

    content = _get(url)
    if content is None:
        return [], errors

    try:
        page_urls, children = parse_sitemap_with_index(content, max_urls=max_urls)
    except ET.ParseError:
        return [], errors + [f"{url}: malformed XML"]

    urls.extend(page_urls)
    for child in children[:10]:
        child_content = _get(child)
        if child_content is not None:
            try:
                urls.extend(parse_sitemap(child_content, max_urls=max_urls))
            except ET.ParseError:
                errors.append(f"{child}: malformed XML")

    return urls[:max_urls], errors