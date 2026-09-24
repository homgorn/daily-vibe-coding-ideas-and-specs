"""Парсер robots.txt: приоритеты, wildcard-политика, sitemap/crawl-delay."""

from __future__ import annotations

from engine.crawl.robots import RobotsTxt


def test_empty_robots_allows_everything():
    r = RobotsTxt("", "https://example.com")
    assert r.is_allowed("https://example.com/anything")
    assert r.sitemaps == []


def test_disallow_root_blocks_all():
    r = RobotsTxt("User-agent: *\nDisallow: /", "https://example.com")
    assert not r.is_allowed("https://example.com/")
    assert not r.is_allowed("https://example.com/docs/guide")


def test_no_matching_rule_allows():
    r = RobotsTxt("User-agent: *\nDisallow: /api\n", "https://example.com")
    assert r.is_allowed("https://example.com/blog/post-1")


def test_longest_match_wins():
    r = RobotsTxt(
        "User-agent: *\nDisallow: /docs\nAllow: /docs/public\n",
        "https://example.com",
    )
    assert not r.is_allowed("https://example.com/docs/private")
    assert r.is_allowed("https://example.com/docs/public/guide")


def test_specific_user_agent_preferred():
    r = RobotsTxt(
        "User-agent: *\nDisallow: /\n"
        "User-agent: DailyVibeEngine\nAllow: /\n",
        "https://example.com",
    )
    assert not r.is_allowed("https://example.com/x", user_agent="*")
    assert r.is_allowed("https://example.com/x", user_agent="DailyVibeEngine")


def test_sitemaps_and_crawl_delay_extracted():
    r = RobotsTxt(
        "User-agent: *\nCrawl-delay: 5\nSitemap: https://example.com/sitemap.xml\n",
        "https://example.com",
    )
    assert r.sitemaps == ["https://example.com/sitemap.xml"]
    assert r.crawl_delay() == 5.0


def test_comments_and_empty_lines_ignored():
    r = RobotsTxt(
        "# comment\n\nUser-agent: *\n# другой коммент\nDisallow: /api\n",
        "https://example.com",
    )
    assert not r.is_allowed("https://example.com/api/v1")