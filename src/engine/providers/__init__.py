"""LLM providers: abstraction, caching, model routing by stage.

Supports OpenRouter/OpenAI/Anthropic/local/OpenCode default.
Cache: hash(prompt) → response.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    cached: bool = False


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...


class MockProvider(LLMProvider):
    def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        return LLMResponse(
            content=f"[MOCK {model}] {prompt[:200]}...",
            model=model,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": 50},
        )

    def list_models(self) -> list[str]:
        return ["mock/default"]


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, referer: str = "", title: str = "DailyVibeEngine"):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.referer = referer
        self.title = title

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.title,
        }
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        return headers

    def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        import urllib.error
        import urllib.request

        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if "temperature" in kwargs:
            body["temperature"] = kwargs["temperature"]

        attempts = int(kwargs.get("retries", 3))
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=json.dumps(body).encode(),
                    headers=self._headers(),
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode())
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                if not content:
                    raise ValueError(f"empty content from {model}")
                return LLMResponse(
                    content=content,
                    model=data.get("model", model),
                    usage=data.get("usage", {}),
                )
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:400]
                last_error = RuntimeError(f"HTTP {exc.code} from {model}: {detail}")
                # 400/401/402/403/404/422 are request or config errors: a wrong
                # model ID or a bad key never succeeds on a retry, so repeating
                # only burns the free-tier budget and hides the real cause.
                # 429 and 5xx are the ones worth repeating.
                if exc.code in (400, 401, 402, 403, 404, 422):
                    raise last_error from exc
            except urllib.error.URLError as exc:
                # Network-level failure (DNS, no route, refused). Every model
                # fails identically, so retrying the fallback chain only
                # multiplies the wait and reports N different model errors for
                # one local connectivity problem.
                raise RuntimeError(f"network unreachable for {model}: {exc.reason}") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
        raise RuntimeError(f"OpenRouter failed after {attempts} attempts: {last_error}")

    def list_models(self) -> list[str]:
        import urllib.request

        req = urllib.request.Request(f"{self.base_url}/models", headers=self._headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return [m["id"] for m in data.get("data", [])]


class ProviderRegistry:
    def __init__(self, config: dict | None = None):
        if config is None:
            from engine.config import load_config
            config = load_config()
        self.config = config
        self.providers: dict[str, LLMProvider] = {}
        self._budget_minutes: dict[str, float | None] = {}
        self._budget_spent: dict[str, float] = {}
        self._init_providers()
        self._init_cache()

    def _init_providers(self):
        self.providers["mock"] = MockProvider()
        from engine.config import secret
        or_key = secret("OPENROUTER_API_KEY")
        if or_key:
            self.providers["openrouter"] = OpenRouterProvider(
                or_key,
                referer=self.config.get("site", {}).get("base_url", ""),
                title=self.config.get("project", {}).get("name", "DailyVibeEngine"),
            )

    def _init_cache(self):
        cache_path = ROOT / self.config.get("cache", {}).get("llm_path", "db/llm_cache.sqlite")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_conn = sqlite3.connect(cache_path)
        self.cache_conn.row_factory = sqlite3.Row
        self.cache_conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                key_hash TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self.cache_conn.commit()

    def _cache_key(self, prompt: str, model: str, **kwargs) -> str:
        data = json.dumps({"p": prompt, "m": model, "k": kwargs}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_cached(self, key: str) -> LLMResponse | None:
        if not self.config.get("cache", {}).get("llm_enabled", True):
            return None
        row = self.cache_conn.execute(
            "SELECT response, model FROM llm_cache WHERE key_hash = ?", (key,)
        ).fetchone()
        if row:
            return LLMResponse(content=row["response"], model=row["model"], cached=True)
        return None

    def _set_cache(self, key: str, response: LLMResponse):
        if not self.config.get("cache", {}).get("llm_enabled", True):
            return
        self.cache_conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key_hash, prompt, response, model) VALUES (?, ?, ?, ?)",
            (key, response.content[:2000], response.content, response.model),
        )
        self.cache_conn.commit()

    def get_model_for_stage(self, stage: str) -> str:
        models = self.config.get("models", {})
        return models.get(stage, models.get("medium", "mock/default"))

    def models_for_stage(self, stage: str) -> list[str]:
        primary = self.get_model_for_stage(stage)
        fallbacks = self.config.get("models", {}).get("fallbacks", {}).get(stage, [])
        ordered = [primary]
        ordered.extend(m for m in fallbacks if m != primary)
        return ordered

    def _stage_kwargs(self, stage: str, kwargs: dict) -> dict:
        models = self.config.get("models", {})
        merged = dict(kwargs)
        per_stage = models.get("max_tokens_by_stage")
        if isinstance(per_stage, dict) and stage in per_stage:
            merged.setdefault("max_tokens", per_stage[stage])
        else:
            merged.setdefault("max_tokens", models.get("max_tokens", 2000))
        temps = models.get("temperature")
        if isinstance(temps, dict) and stage in temps:
            merged.setdefault("temperature", temps[stage])
        return merged

    def start_budget(self, stage: str) -> None:
        minutes = self.config.get("models", {}).get("budget_minutes", {}).get(stage)
        self._budget_minutes[stage] = float(minutes) if minutes else None
        self._budget_spent[stage] = 0.0

    def budget_exhausted(self, stage: str) -> bool:
        limit = self._budget_minutes.get(stage)
        if not limit:
            return False
        return self._budget_spent.get(stage, 0.0) >= limit * 60

    def budget_report(self) -> dict[str, float]:
        return {k: round(v / 60, 2) for k, v in self._budget_spent.items() if v > 0}

    def complete(self, prompt: str, stage: str = "medium", **kwargs) -> LLMResponse:
        provider_name = self.config.get("models", {}).get("provider", "mock")
        provider = self.providers.get(provider_name) or self.providers["mock"]

        # `cache` is a registry-level concern, never a provider request kwarg.
        use_cache = bool(kwargs.pop("cache", True))
        call_kwargs = self._stage_kwargs(stage, kwargs)
        candidates = self.models_for_stage(stage)
        errors: list[str] = []
        if stage not in self._budget_spent:
            self._budget_spent[stage] = 0.0

        for model in candidates:
            cache_key = self._cache_key(prompt, model, **call_kwargs)
            if use_cache:
                cached = self._get_cached(cache_key)
                if cached:
                    return cached
            if self.budget_exhausted(stage):
                raise RuntimeError(
                    f"budget exhausted for stage={stage} "
                    f"({self._budget_minutes.get(stage)} min); remaining models skipped"
                )
            started = time.monotonic()
            try:
                response = provider.complete(prompt, model, **call_kwargs)
            except Exception as exc:  # noqa: BLE001
                self._budget_spent[stage] += time.monotonic() - started
                errors.append(f"{model}: {exc}")
                continue
            self._budget_spent[stage] += time.monotonic() - started
            if use_cache:
                self._set_cache(cache_key, response)
            return response

        raise RuntimeError(
            f"all models failed for stage={stage}; tried {candidates}. "
            + " | ".join(errors)
        )

    def close(self):
        if hasattr(self, "cache_conn"):
            self.cache_conn.close()


_registry: ProviderRegistry | None = None


def get_provider(config: dict | None = None) -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry(config)
    return _registry


def complete(prompt: str, stage: str = "medium", **kwargs) -> LLMResponse:
    return get_provider().complete(prompt, stage, **kwargs)