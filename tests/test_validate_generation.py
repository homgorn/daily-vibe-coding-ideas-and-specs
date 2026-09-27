"""Validator must reject specs the generator failed to fill in."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.spec import FALLBACK_MARKER  # noqa: E402
from engine.validate import validate_artifact  # noqa: E402

HEAD = """---
title: "A spec"
description: "A description that is long enough to satisfy the length rule for sure."
tags: ["x"]
origin: research
viability_score: 60
date: 2026-01-01
---

# A spec

## Problem

Some real problem text here with a citation [1](https://en.wikipedia.org/wiki/Thing).

## Solution

A real solution.

## Cited Sources

[1] Thing — https://en.wikipedia.org/wiki/Thing
"""


def test_filled_spec_passes(tmp_path):
    path = tmp_path / "ok.md"
    path.write_text(HEAD, encoding="utf-8")
    report = validate_artifact(path, "spec")
    assert report.passed, [r.errors for r in report.results if not r.passed]


def test_fallback_spec_is_rejected(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text(
        HEAD.replace("## Solution\n\nA real solution.", f"{FALLBACK_MARKER}\n\n## Solution\n\n"),
        encoding="utf-8",
    )
    report = validate_artifact(path, "spec")
    assert not report.passed
    failed = [r for r in report.results if not r.passed]
    assert any(r.agent == "generation" for r in failed), [r.agent for r in failed]


def test_missing_file_still_reports_structure(tmp_path):
    report = validate_artifact(tmp_path / "nope.md", "spec")
    assert not report.passed
    assert any(r.agent == "structure" for r in report.results)
