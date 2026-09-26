"""LLM providers: abstraction, caching, model routing by stage.

Supports OpenRouter/OpenAI/Anthropic/local/OpenCode default.
Cache: hash(prompt) → response.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
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
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        import urllib.request
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 4096),
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        choice = data.get("choices", [{}])[0]
        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            model=model,
            usage=data.get("usage", {}),
        )

    def list_models(self) -> list[str]:
        return ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-70b-instruct"]


class ProviderRegistry:
    def __init__(self, config: dict | None = None):
        if config is None:
            from engine.config import load_config
            config = load_config()
        self.config = config
        self.providers: dict[str, LLMProvider] = {}
        self._init_providers()
        self._init_cache()

    def _init_providers(self):
        self.providers["mock"] = MockProvider()
        from engine.config import secret
        or_key = secret("OPENROUTER_API_KEY")
        if or_key:
            self.providers["openrouter"] = OpenRouterProvider(or_key)

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

    def complete(self, prompt: str, stage: str = "medium", **kwargs) -> LLMResponse:
        model = self.get_model_for_stage(stage)
        provider_name = self.config.get("models", {}).get("provider", "mock")
        provider = self.providers.get(provider_name) or self.providers["mock"]

        cache_key = self._cache_key(prompt, model, **kwargs)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = provider.complete(prompt, model, **kwargs)
        self._set_cache(cache_key, response)
        return response

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