"""Spec generation: LLM JSON must be parsed, fallback must be loud."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.spec as spec_mod  # noqa: E402
from engine.providers import LLMResponse  # noqa: E402

IDEA = {
    "id": 42,
    "title": "Repo Rater — ranks GitHub repos by vibe-coding readiness",
    "summary": "Ranks new repos so builders know what to fork first.",
    "viability": {"score": 72, "confidence": 60},
    "tags": ["tools"],
    "status": "new",
    "origin": "research",
}
ITEMS = [
    {
        "title": "some/repo",
        "url": "https://github.com/some/repo",
        "description": "A tool",
        "source_name": "github",
        "meta": "{}",
    }
]

GOOD_PAYLOAD = (
    "## Problem\n\nBuilders waste days on abandoned repos [source:0].\n\n"
    "## Cited Sources\n\n[1] some/repo — https://github.com/some/repo"
)


class FakeProvider:
    def __init__(self, content: str):
        self.content = content

    def complete(self, prompt, model, **kwargs):
        return LLMResponse(content=self.content, model=model)

    def list_models(self):
        return []


def patch(monkeypatch, content: str):
    monkeypatch.setattr(spec_mod, "complete", lambda p, stage=None, **kw: FakeProvider(content).complete(p, "m"))


def test_plain_json_is_used(monkeypatch):
    patch(monkeypatch, '{"problem": "## Problem\\n\\nReal A", "cited_sources": "## Cited Sources\\n\\n[1] x — https://y"}')
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "Real A" in out
    assert "See summary above." not in out


def test_fenced_json_is_used(monkeypatch):
    patch(monkeypatch, '```json\n{"problem": "## Problem\\n\\nFenced body"}\n```')
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "Fenced body" in out
    assert "See summary above." not in out


def test_bare_fence_is_used(monkeypatch):
    patch(monkeypatch, '```\n{"problem": "## Problem\\n\\nBare fence body"}\n```')
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "Bare fence body" in out


def test_prose_around_json_is_used(monkeypatch):
    patch(
        monkeypatch,
        'Sure! Here is the spec:\n\n{"problem": "## Problem\\n\\nWith prose around it"}\n\n'
        "Hope this helps.",
    )
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "With prose around it" in out


def test_missing_fields_do_not_become_tbd(monkeypatch):
    patch(monkeypatch, '{"problem": "## Problem\\n\\nOnly one field returned"}')
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "TBD" not in out


def test_fallback_is_marked_not_silent(monkeypatch):
    patch(monkeypatch, "I cannot do that.")
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert spec_mod.FALLBACK_MARKER in out
    assert "TBD" not in out


def test_fallback_marker_contains_no_fabricated_citations(monkeypatch):
    patch(monkeypatch, "nope")
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "Generated from fetched items" not in out
