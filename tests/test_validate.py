"""Tests for validate module: 5 agents + SEO/GEO + legal."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.validate import (
    parse_frontmatter,
    extract_urls,
    check_data_agent,
    check_text_agent,
    check_seo_geo,
    check_legal,
    check_post_agent,
    check_image_agent,
    check_video_agent,
    validate_artifact,
)


GOOD_FRONTMATTER = """---
title: "AI Agent Framework Comparison 2026"
tags: [ai-agents, mcp, comparison]
origin: research
viability_score: 78
description: "A detailed comparison of the top AI agent frameworks in 2026, covering features, pricing, and best use cases for developers."
canonical: https://example.com/ai-agents
---

# AI Agent Framework Comparison 2026

## Problem
Developers need to choose between dozens of AI agent frameworks.

## FAQ
**Q: What is the best AI agent framework?**
A: It depends on your use case.

## Cited Sources
[1] Anthropic Docs — https://docs.anthropic.com — 2026-08-13
"""

BAD_CONTENT = """Some random text without frontmatter.
TODO: fix this.
"""


def test_parse_frontmatter():
    fm, body = parse_frontmatter(GOOD_FRONTMATTER)
    assert fm["title"].strip('"') == "AI Agent Framework Comparison 2026"
    assert fm["viability_score"] == 78
    assert isinstance(fm["tags"], list)
    assert "AI Agent Framework" in body


def test_parse_frontmatter_none():
    fm, body = parse_frontmatter("Just plain text")
    assert fm == {}
    assert body == "Just plain text"


def test_extract_urls():
    text = "See https://example.com/page and https://other.org/x."
    urls = extract_urls(text)
    assert "https://example.com/page" in urls
    assert any("https://other.org/x" in u for u in urls)


def test_data_agent_pass():
    fm, _ = parse_frontmatter(GOOD_FRONTMATTER)
    result = check_data_agent(GOOD_FRONTMATTER, fm)
    assert result.passed
    assert result.errors == []


def test_text_agent_pass():
    fm, _ = parse_frontmatter(GOOD_FRONTMATTER)
    result = check_text_agent(GOOD_FRONTMATTER, fm)
    assert result.passed
    assert result.errors == []


def test_text_agent_missing_frontmatter():
    result = check_text_agent(BAD_CONTENT, {})
    assert not result.passed
    assert any("frontmatter" in e.lower() or "Missing" in e for e in result.errors)


def test_seo_geo_pass():
    fm, _ = parse_frontmatter(GOOD_FRONTMATTER)
    result = check_seo_geo(GOOD_FRONTMATTER, fm)
    assert result.passed
    # Should have warnings for missing og_image but no errors
    assert result.errors == []


def test_seo_geo_multiple_h1():
    content = GOOD_FRONTMATTER + "\n# Another H1\n# Third H1\n"
    fm, _ = parse_frontmatter(content)
    result = check_seo_geo(content, fm)
    assert not result.passed
    assert any("H1" in e for e in result.errors)


def test_seo_geo_title_too_long():
    fm = {"title": "A" * 70, "description": "B" * 140}
    result = check_seo_geo("x" * 500, fm)
    # Title too long is a warning, not error
    assert any("too long" in w.lower() for w in result.warnings)


def test_legal_investment_no_disclaimer():
    content = "This investment opportunity promises revenue projection of 100%."
    result = check_legal(content, {})
    assert not result.passed
    assert any("disclaimer" in e.lower() for e in result.errors)


def test_legal_investment_with_disclaimer():
    content = "This investment opportunity. Not financial advice. DYOR."
    result = check_legal(content, {})
    assert result.passed


def test_image_agent_no_images():
    fm, _ = parse_frontmatter(GOOD_FRONTMATTER)
    result = check_image_agent(GOOD_FRONTMATTER, fm)
    assert result.passed
    assert any("og_image" in w for w in result.warnings)


def test_video_agent_normal_content():
    result = check_video_agent(BAD_CONTENT, {})
    assert result.passed


def test_post_agent():
    result = check_post_agent("x" * 100, {"description": "A" * 140})
    assert result.passed

def test_parse_frontmatter_quoted_value():
    fm, _ = parse_frontmatter('---\ntitle: "Hello World"\n---\nBody')
    assert fm["title"].strip('"') == "Hello World"


def test_validate_artifact_nonexistent():
    report = validate_artifact("/nonexistent/file.md")
    assert not report.passed
    assert any(r.agent == "structure" for r in report.results)


def test_validate_artifact_good(tmp_path):
    md = tmp_path / "test.md"
    md.write_text(GOOD_FRONTMATTER, encoding="utf-8")
    report = validate_artifact(md, "idea", check_links_online=False)
    assert report.passed
    assert len(report.results) == 8  # 5 agents + seo_geo + links + legal