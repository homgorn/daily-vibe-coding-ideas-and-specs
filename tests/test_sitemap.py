"""Парсер sitemap: XML urlset, gzip, sitemapindex-рекурсия."""

from __future__ import annotations

import gzip

from engine.crawl.sitemap import parse_sitemap, parse_sitemap_with_index

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/blog/one</loc></url>
  <url><loc>https://example.com/blog/two</loc></url>
</urlset>"""

INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-blog.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""


def test_parse_plain_urlset():
    urls = parse_sitemap(URLSET.encode())
    assert urls == [
        "https://example.com/",
        "https://example.com/blog/one",
        "https://example.com/blog/two",
    ]


def test_parse_gzip_urlset():
    urls = parse_sitemap(gzip.compress(URLSET.encode()))
    assert len(urls) == 3


def test_sitemapindex_returns_children():
    urls, children = parse_sitemap_with_index(INDEX.encode())
    assert urls == []
    assert children == [
        "https://example.com/sitemap-blog.xml",
        "https://example.com/sitemap-pages.xml",
    ]


def test_max_urls_respected():
    urls = parse_sitemap(URLSET.encode(), max_urls=2)
    assert len(urls) == 2