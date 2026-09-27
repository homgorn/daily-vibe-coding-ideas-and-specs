"""Spec generation is split into per-group calls, not one giant JSON blob."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.spec as spec_mod  # noqa: E402
from engine.providers import LLMResponse  # noqa: E402

IDEA = {
    "id": 7,
    "title": "Repo Rater",
    "summary": "Ranks new repos.",
    "viability": {"score": 70, "confidence": 50},
    "tags": ["tools"],
    "status": "new",
    "origin": "research",
}
ITEMS = [{"title": "x/y", "url": "https://example.org/x", "description": "d",
          "source_name": "github", "meta": "{}"}]

ALL_SECTIONS = [key for key, _ in spec_mod.SPEC_SECTIONS]


class Recorder:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, prompt, stage=None, **kwargs):
        self.calls.append(prompt)
        for marker, payload in self.responses.items():
            if marker in prompt:
                return LLMResponse(content=payload, model="m")
        return LLMResponse(content='{"x": "## X\\n\\nbody"}', model="m")


def requested_keys(prompt: str) -> list[str]:
    return [key for key in ALL_SECTIONS if f'"{key}"' in prompt]


def cooperative(prompt, stage=None, **kwargs):
    """Answer with exactly the keys asked for — the good case."""
    keys = requested_keys(prompt)
    payload = {key: f"## {key.upper()}\\n\\nbody for {key}" for key in keys}
    return LLMResponse(content=json.dumps(payload), model="m")


def test_sections_are_split_into_several_calls(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(spec_mod, "complete", rec)
    spec_mod.generate_spec(IDEA, ITEMS)
    assert len(rec.calls) > 1, "one giant call is what breaks on long specs"
    for prompt in rec.calls:
        assert requested_keys(prompt), "a call with no sections requested is wasted"


def test_cooperative_model_needs_no_retries(monkeypatch):
    """Every group answered fully: exactly one call per group, no wasted work."""
    calls: list[str] = []
    counter = Recorder()

    def counting(prompt, stage=None, **kwargs):
        calls.append(prompt)
        return cooperative(prompt)

    monkeypatch.setattr(spec_mod, "complete", counting)
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert len(calls) == len(spec_mod.SPEC_GROUPS), (
        f"expected {len(spec_mod.SPEC_GROUPS)} calls, made {len(calls)}"
    )
    assert "not provided by model" not in out
    assert spec_mod.FALLBACK_MARKER not in out
    counter.calls.clear()


def test_every_section_is_covered_by_exactly_one_group():
    covered: list[str] = []
    for _group, keys in spec_mod.SPEC_GROUPS:
        covered.extend(keys)
    assert sorted(covered) == sorted(ALL_SECTIONS)
    assert len(covered) == len(set(covered)), "a section must not be requested twice"


def test_group_content_is_assembled(monkeypatch):
    payloads = {
        "Problem": '{"problem": "## Problem\\n\\nREAL PROBLEM TEXT"}',
        "Tech Stack": '{"tech_stack": "## Tech Stack & Architecture\\n\\nRUST"}',
        "Monetization": '{"monetization": "## Monetization\\n\\nPAID TIER"}',
    }
    monkeypatch.setattr(spec_mod, "complete", Recorder(payloads))
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "REAL PROBLEM TEXT" in out
    assert "RUST" in out
    assert "PAID TIER" in out
    assert spec_mod.FALLBACK_MARKER not in out


def test_one_failing_group_does_not_ruin_the_spec(monkeypatch):
    def flaky(prompt, stage=None, **kwargs):
        if "Monetization" in prompt:
            raise RuntimeError("429 rate-limited")
        return LLMResponse(content='{"problem": "## Problem\\n\\nSURVIVED"}', model="m")

    monkeypatch.setattr(spec_mod, "complete", flaky)
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "SURVIVED" in out
    assert spec_mod.FALLBACK_MARKER not in out, (
        "one lost group must not invalidate the sections that succeeded"
    )
    assert "not provided by model" in out


def test_all_groups_failing_uses_marker(monkeypatch):
    def dead(prompt, stage=None, **kwargs):
        raise RuntimeError("all down")

    monkeypatch.setattr(spec_mod, "complete", dead)
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert spec_mod.FALLBACK_MARKER in out


def test_no_group_prompt_asks_for_too_many_sections(monkeypatch):
    """Each call must stay small enough to finish before the cap."""
    rec = Recorder()
    monkeypatch.setattr(spec_mod, "complete", rec)
    spec_mod.generate_spec(IDEA, ITEMS)
    for prompt in rec.calls:
        requested = sum(1 for key in ALL_SECTIONS if f'"{key}"' in prompt)
        assert requested <= spec_mod.MAX_SECTIONS_PER_CALL, (
            f"one call asked for {requested} sections"
        )


def test_truncated_group_is_retried(monkeypatch):
    """A truncated (unparseable) group is retried, not just marked missing.

    Truncation was the measured failure mode: JSON escaping burns tokens, so
    a 4-section group can exceed the cap and come back mid-string. Giving up
    there would lose four sections that one retry usually recovers.
    """
    calls: list[str] = []

    def flaky(prompt, stage=None, **kwargs):
        calls.append(prompt)
        if len(calls) == 1:
            # Truncated: valid opening, no closing brace.
            return LLMResponse(content='{"problem": "## Problem\\n\\ncut off mid', model="m")
        if "Architecture" in prompt:
            return LLMResponse(
                content='{"tech_stack": "## Tech Stack & Architecture\\n\\nRUST"}', model="m"
            )
        return LLMResponse(content='{"problem": "## Problem\\n\\nRECOVERED"}', model="m")

    monkeypatch.setattr(spec_mod, "complete", flaky)
    out = spec_mod.generate_spec(IDEA, ITEMS)
    assert "RECOVERED" in out
    assert spec_mod.FALLBACK_MARKER not in out


def group_of(prompt: str) -> str:
    marker = "Write ONLY these sections of the spec: "
    for line in prompt.splitlines():
        if line.startswith(marker):
            return line[len(marker):].strip()
    return "?"


def test_group_missing_keys_is_retried(monkeypatch):
    """If a group answers only some of its keys, ask again for the rest."""
    attempts: dict[str, int] = {}

    def withhold_one_on_first_attempt(prompt, stage=None, **kwargs):
        name = group_of(prompt)
        attempts[name] = attempts.get(name, 0) + 1
        keys = requested_keys(prompt)
        if attempts[name] == 1:
            keys = keys[:-1]
        payload = {key: f"## {key.upper()}\\n\\nbody for {key}" for key in keys}
        return LLMResponse(content=json.dumps(payload), model="m")

    monkeypatch.setattr(spec_mod, "complete", withhold_one_on_first_attempt)
    out = spec_mod.generate_spec(IDEA, ITEMS)

    assert set(attempts.values()) == {spec_mod.MAX_GROUP_ATTEMPTS}, (
        f"each group should be retried exactly once: {attempts}"
    )
    assert "not provided by model" not in out, "every section should have been filled"
    assert spec_mod.FALLBACK_MARKER not in out


def test_retry_asks_only_for_missing_keys(monkeypatch):
    """A retry must not re-request sections that already succeeded."""
    asked: list[list[str]] = []
    served: set[str] = set()

    def withhold_features_once(prompt, stage=None, **kwargs):
        keys = requested_keys(prompt)
        asked.append(keys)
        if "features" in keys and "features" not in served:
            served.add("features")
            keys = [key for key in keys if key != "features"]
        payload = {key: f"## {key.upper()}\\n\\nbody for {key}" for key in keys}
        return LLMResponse(content=json.dumps(payload), model="m")

    monkeypatch.setattr(spec_mod, "complete", withhold_features_once)
    out = spec_mod.generate_spec(IDEA, ITEMS)

    retry = asked[1]
    assert "features" in retry
    for already in ("problem", "solution", "target_user"):
        assert already not in retry, f"{already} was already filled; re-asking wastes budget"
    assert "not provided by model" not in out


def test_spec_calls_are_not_memoized(monkeypatch):
    """Spec calls must bypass the cache.

    Measured: 30 of 85 cached responses were truncated. A memoized truncated
    response is replayed verbatim, so every retry got the same broken text and
    the group could never recover.
    """
    seen: list[dict] = []

    def record(prompt, stage=None, **kwargs):
        seen.append(kwargs)
        keys = requested_keys(prompt)
        payload = {key: f"## {key.upper()}\\n\\nbody" for key in keys}
        return LLMResponse(content=json.dumps(payload), model="m")

    monkeypatch.setattr(spec_mod, "complete", record)
    spec_mod.generate_spec(IDEA, ITEMS)
    assert seen, "no calls recorded"
    for kwargs in seen:
        assert kwargs.get("cache") is False, "spec calls must not read/write the cache"


def test_retry_prompt_differs_from_the_first_attempt(monkeypatch):
    """A retry must be a different request, not a verbatim replay."""
    prompts: list[str] = []

    def truncated_once(prompt, stage=None, **kwargs):
        prompts.append(prompt)
        keys = requested_keys(prompt)
        if len(prompts) == 1:
            return LLMResponse(content='{"problem": "## Problem\\n\\ncut', model="m")
        payload = {key: f"## {key.upper()}\\n\\nbody" for key in keys}
        return LLMResponse(content=json.dumps(payload), model="m")

    monkeypatch.setattr(spec_mod, "complete", truncated_once)
    spec_mod.generate_spec(IDEA, ITEMS)
    assert len(prompts) >= 2, "expected a retry"
    assert prompts[0] != prompts[1], "a retry reused the identical prompt"
    assert "attempt 2" in prompts[1], "the retry should tell the model it failed"


def test_retries_are_bounded(monkeypatch):
    """A group that never yields anything must not retry forever."""
    calls = {"n": 0}

    def always_bad(prompt, stage=None, **kwargs):
        calls["n"] += 1
        return LLMResponse(content='{"problem": "## Problem\\n\\nonly one"}', model="m")

    monkeypatch.setattr(spec_mod, "complete", always_bad)
    spec_mod.generate_spec(IDEA, ITEMS)
    assert calls["n"] == len(spec_mod.SPEC_GROUPS) * spec_mod.MAX_GROUP_ATTEMPTS
