"""Providers: stage routing, fallbacks, budget, cache."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.providers import LLMResponse, MockProvider, ProviderRegistry  # noqa: E402


def make_registry(tmp_path, models: dict) -> ProviderRegistry:
    cfg = {
        "models": models,
        "cache": {"llm_enabled": True, "llm_path": str(tmp_path / "c.sqlite")},
    }
    reg = ProviderRegistry(cfg)
    reg.providers["mock"] = MockProvider()
    return reg


def test_stage_models_primary_first(tmp_path):
    reg = make_registry(
        tmp_path,
        {
            "provider": "mock",
            "cheap": "a",
            "medium": "b",
            "expensive": "c",
            "fallbacks": {"cheap": ["d", "a"]},
        },
    )
    assert reg.models_for_stage("cheap") == ["a", "d"]
    reg.close()


def test_stage_kwargs_use_per_stage_limits(tmp_path):
    reg = make_registry(
        tmp_path,
        {
            "provider": "mock",
            "max_tokens": 2000,
            "max_tokens_by_stage": {"cheap": 700, "expensive": 2000},
            "temperature": {"cheap": 0.2, "medium": 0.4},
        },
    )
    assert reg._stage_kwargs("cheap", {})["max_tokens"] == 700
    assert reg._stage_kwargs("expensive", {})["max_tokens"] == 2000
    assert reg._stage_kwargs("medium", {})["max_tokens"] == 2000
    assert reg._stage_kwargs("cheap", {})["temperature"] == 0.2
    assert "temperature" not in reg._stage_kwargs("expensive", {})
    reg.close()


def test_falls_back_when_primary_fails(tmp_path):
    reg = make_registry(
        tmp_path,
        {"provider": "mock", "expensive": "boom", "fallbacks": {"expensive": ["good"]}},
    )

    class Flaky:
        def __init__(self):
            self.calls: list[str] = []

        def complete(self, prompt, model, **kwargs):
            self.calls.append(model)
            if model == "boom":
                raise RuntimeError("429 rate-limited")
            return LLMResponse(content="ok", model=model)

        def list_models(self):
            return ["boom", "good"]

    flaky = Flaky()
    reg.providers["mock"] = flaky
    resp = reg.complete("hi", stage="expensive")
    assert resp.content == "ok"
    assert flaky.calls == ["boom", "good"]
    reg.close()


def test_raises_when_every_model_fails(tmp_path):
    reg = make_registry(
        tmp_path,
        {
            "provider": "mock",
            "expensive": "boom",
            "fallbacks": {"expensive": ["also-bad"]},
        },
    )

    class Dead:
        def complete(self, prompt, model, **kwargs):
            raise RuntimeError("down")

        def list_models(self):
            return []

    reg.providers["mock"] = Dead()
    with pytest.raises(RuntimeError, match="all models failed"):
        reg.complete("hi", stage="expensive")
    reg.close()


def test_budget_blocks_further_calls(tmp_path):
    reg = make_registry(
        tmp_path,
        {"provider": "mock", "expensive": "m", "budget_minutes": {"expensive": 0.001}},
    )

    class Slow:
        def complete(self, prompt, model, **kwargs):
            import time

            time.sleep(0.09)
            return LLMResponse(content="ok", model=model)

        def list_models(self):
            return ["m"]

    reg.providers["mock"] = Slow()
    reg.start_budget("expensive")
    with pytest.raises(RuntimeError, match="budget exhausted"):
        for i in range(200):
            reg.complete(f"unique prompt {i}", stage="expensive")
    assert reg.budget_exhausted("expensive")
    assert reg._budget_spent["expensive"] > 0
    reg.close()


def test_budget_inactive_without_limit(tmp_path):
    reg = make_registry(tmp_path, {"provider": "mock", "expensive": "m"})
    reg.start_budget("expensive")
    assert not reg.budget_exhausted("expensive")
    reg.close()


def test_cache_hit_skips_provider(tmp_path):
    reg = make_registry(tmp_path, {"provider": "mock", "medium": "m"})

    class Counter:
        def __init__(self):
            self.n = 0

        def complete(self, prompt, model, **kwargs):
            self.n += 1
            return LLMResponse(content="same", model=model)

        def list_models(self):
            return []

    counter = Counter()
    reg.providers["mock"] = counter
    reg.complete("identical prompt", stage="medium")
    reg.complete("identical prompt", stage="medium")
    assert counter.n == 1
    reg.close()


def test_shipped_config_points_at_real_provider():
    from engine.config import load_config

    provider = load_config()["models"].get("provider")
    assert provider in ("mock", "openrouter", "opencode", "openai"), provider


def test_config_errors_are_not_retried():
    """A bad model ID or key never succeeds on a retry, so it must fail fast.

    Retrying a typo'd model id four times per fallback chain burns the
    free-tier budget and hides the real cause behind a timeout-looking error.
    """
    import io
    import urllib.error
    import urllib.request

    from engine.providers import OpenRouterProvider

    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        body = io.BytesIO(b'{"error":{"message":"not a valid model ID","code":400}}')
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, body)

    original = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        provider = OpenRouterProvider("key")
        with pytest.raises(RuntimeError, match="400"):
            provider.complete("hi", "typo/model:free", max_tokens=100, retries=4)
    finally:
        urllib.request.urlopen = original

    assert calls["n"] == 1, f"400 should be attempted once, got {calls['n']}"


def test_rate_limit_is_retried():
    import io
    import urllib.error
    import urllib.request

    from engine.providers import OpenRouterProvider

    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            body = io.BytesIO(b'{"error":{"message":"rate-limited","code":429}}')
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, body)
        payload = (
            b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}],'
            b'"usage":{"completion_tokens":2}}'
        )
        return io.BytesIO(payload)

    original = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        provider = OpenRouterProvider("key")
        resp = provider.complete("hi", "good/model:free", max_tokens=100, retries=4)
    finally:
        urllib.request.urlopen = original

    assert resp.content == "ok"
    assert calls["n"] == 3


def test_network_failure_is_not_retried_per_model():
    """A DNS/socket failure hits every model identically — stop the chain at once.

    During a network outage this otherwise cost 3 attempts x 3 models x 3 spec
    groups of pure waiting, then reported three different-looking model errors
    for what is a single local connectivity problem.
    """
    import urllib.error
    import urllib.request

    from engine.providers import OpenRouterProvider

    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.URLError("getaddrinfo failed")

    original = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        provider = OpenRouterProvider("key")
        with pytest.raises(RuntimeError, match="getaddrinfo"):
            provider.complete("hi", "any/model:free", max_tokens=100, retries=4)
    finally:
        urllib.request.urlopen = original

    assert calls["n"] == 1, f"network error should be attempted once, got {calls['n']}"
