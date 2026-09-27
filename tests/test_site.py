"""Static site generation tests (link integrity, output structure)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.publish.site as site_mod


def _write_idea(src_dir: Path) -> None:
    ideas = src_dir / "ideas"
    ideas.mkdir(parents=True)
    # The frontmatter must satisfy validation: build_site() refuses to render
    # artifacts that fail any agent, so a half-filled fixture would be
    # (correctly) dropped from the output.
    (ideas / "1_test_idea.md").write_text(
        "---\n"
        "title: Test idea\n"
        "description: A test idea with enough description text to pass the length rule.\n"
        "viability_score: 80\n"
        "viability_confidence: 60\n"
        "origin: research\n"
        "date: 2026-01-01\n"
        "tags: [ai, tools]\n"
        "---\n\n"
        "# Test idea\n\n"
        "Body text with [link](../index.html).\n\n"
        "## Problem\n\nA problem worth solving, cited [1](https://en.wikipedia.org/wiki/Thing).\n\n"
        "## Cited Sources\n\n[1] Thing — https://en.wikipedia.org/wiki/Thing\n",
        encoding="utf-8",
    )


def test_build_site_with_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(site_mod, "SITE_DIR", tmp_path / "site")
    src = tmp_path / "publish_en"
    _write_idea(src)

    stats = site_mod.build_site(config={}, source_dir=src)

    assert stats["broken_links"] == []
    assert stats["ideas"] == 1
    out = tmp_path / "site"
    for rel in (
        "index.html",
        "ideas/index.html",
        "ideas/idea-1-test-idea.html",
        "specs/index.html",
        "rss.xml",
        "sitemap.xml",
        "robots.txt",
        ".nojekyll",
        "assets/style.css",
    ):
        assert (out / rel).exists(), rel
    listing = (out / "ideas" / "index.html").read_text(encoding="utf-8")
    assert 'href="idea-1-test-idea.html"' in listing
    assert 'href="ideas/idea-1-test-idea.html"' not in listing


def test_build_site_empty_source(tmp_path, monkeypatch):
    monkeypatch.setattr(site_mod, "SITE_DIR", tmp_path / "site")

    stats = site_mod.build_site(config={}, source_dir=tmp_path / "nothing")

    assert stats["broken_links"] == []
    assert stats["pages"] >= 5
    assert (tmp_path / "site" / "index.html").exists()


def test_build_site_has_no_local_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(site_mod, "SITE_DIR", tmp_path / "site")
    monkeypatch.setattr(site_mod, "ROOT", tmp_path)
    src = tmp_path / "publish_en"
    _write_idea(src)
    dash = tmp_path / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    (dash / "index.html").write_text("<html><body>dash</body></html>", encoding="utf-8")
    (dash / "data.json").write_text(
        json.dumps({"path": str(tmp_path / "data" / "x.md"), "n": 1}), encoding="utf-8"
    )

    site_mod.build_site(config={}, source_dir=src)

    pattern = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
    for p in (tmp_path / "site").rglob("*"):
        if p.is_file() and p.suffix in (".html", ".xml", ".json", ".txt"):
            text = p.read_text(encoding="utf-8", errors="replace")
            assert not pattern.search(text), f"{p.name} leaks a local absolute path"
    copied = json.loads((tmp_path / "site" / "dashboard" / "data.json").read_text(encoding="utf-8"))
    assert copied["path"] == "x.md"
