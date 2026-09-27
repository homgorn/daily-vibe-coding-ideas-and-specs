"""Site build must not publish artifacts that fail validation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.spec import FALLBACK_MARKER  # noqa: E402
from engine.publish.site import build_site  # noqa: E402

GOOD_SPEC = """---
title: "Good Spec"
description: "A valid description that comfortably exceeds the minimum length rule."
tags: ["ai"]
idea_id: 1
date: 2026-01-01
viability_score: 70
viability_confidence: 60
origin: research
---

# Good Spec

## Problem

Real problem text [1](https://en.wikipedia.org/wiki/Thing).

## Solution

Real solution text.

## Cited Sources

[1] Thing — https://en.wikipedia.org/wiki/Thing
"""

BROKEN_SPEC = GOOD_SPEC.replace("title: \"Good Spec\"", "title: \"Broken Spec\"").replace(
    "## Solution\n\nReal solution text.",
    f"{FALLBACK_MARKER}\n\n## Solution\n\n",
).replace("idea_id: 1", "idea_id: 2")


def make_source(tmp_path: Path) -> Path:
    src = tmp_path / "publish" / "en"
    (src / "specs").mkdir(parents=True)
    (src / "ideas").mkdir(parents=True)
    (src / "specs" / "1_good.md").write_text(GOOD_SPEC, encoding="utf-8")
    (src / "specs" / "2_broken.md").write_text(BROKEN_SPEC, encoding="utf-8")
    return src


def test_failed_spec_is_not_published(tmp_path):
    src = make_source(tmp_path)
    out = tmp_path / "site"
    stats = build_site(
        config={"site": {"base_url": "https://x.test"}},
        source_dir=src,
        out_dir=out,
    )
    published = sorted(p.name for p in (out / "specs").glob("spec-*.html"))
    assert published, "the valid spec should be published"
    assert all("2-" not in name for name in published), published
    assert stats["excluded"] >= 1
    assert stats["excluded_names"], "exclusion must be reported, not silent"


def test_excluded_spec_body_absent_from_site(tmp_path):
    src = make_source(tmp_path)
    out = tmp_path / "site"
    build_site(
        config={"site": {"base_url": "https://x.test"}},
        source_dir=src,
        out_dir=out,
    )
    combined = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in out.rglob("*.html")
    )
    assert "spec-generation-failed" not in combined
