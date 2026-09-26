# ADR-005: LLM provider abstraction with stage-based routing

**Date**: 2026-09-24
**Status**: Accepted
**Deciders**: Owner
**Consulted**: Agent

## Context

Constitution §4: "LLM-кэш обязателен; бюджет токенов контролируется; дешёвая модель — на массовые операции." Plan §46.5: "free/дешёвая модель — fetch, аннотации, OCR; дорогая — синтез, спеки; кэш на пересборках." The project uses LLM at multiple stages with very different cost profiles.

## Decision

Implement a **Provider abstraction** (`src/engine/providers/`) with:
1. **Stage-based model routing**: `cheap` (fetch/annotate), `medium` (cluster/summarize), `expensive` (synthesize/spec)
2. **SQLite cache**: `db/llm_cache.sqlite` with `sha256(prompt+model+kwargs)` → response
3. **Provider registry**: mock (default), OpenRouter, OpenCode — selected by config
4. **Global singleton**: `get_provider()` returns shared instance

## Consequences

### Positive
- Cache eliminates redundant LLM calls on re-runs (big cost savings)
- Stage routing: cheap models for high-volume, expensive for critical synthesis
- Provider swappable without changing call sites
- Mock provider allows full pipeline testing without API keys

### Negative
- Cache grows unboundedly (needs periodic cleanup)
- Mock responses don't produce real synthesis quality
- Single global instance (not thread-safe, acceptable for CLI)

### Neutral
- Cache key includes model name (different models cached separately)
- Config-driven: `models.cheap/medium/expensive` in config.yaml

## Alternatives Considered

| Alternative | Pros | Cons | Why rejected |
|-------------|------|------|--------------|
| Direct API calls everywhere | Simple | No cache, no routing, high cost | Violates constitution §4 |
| No cache (always fresh) | Always current | Expensive on re-runs | Violates constitution §4 |
| External cache (Redis) | Shared, fast | Extra dependency, overkill | SQLite sufficient for single process |

## Compliance

- [x] Data is truth — LLM responses cached verbatim
- [x] Validation before publication — LLM output still validated
- [x] Secrets only in .env — API keys via `secret()`
- [x] Markdown + index — LLM outputs written to MD

## References

- `constitution.md` § 4
- `plan.md` § Ключевые решения #5
- `config.yaml` § models, § cache
- `src/engine/providers/__init__.py`
