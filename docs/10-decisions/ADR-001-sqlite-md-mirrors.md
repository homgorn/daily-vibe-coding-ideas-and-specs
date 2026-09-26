# ADR-001: SQLite as primary datastore with Markdown mirrors

**Date**: 2026-08-13
**Status**: Accepted
**Deciders**: Owner
**Consulted**: Agent

## Context

The project needs to store 30+ items/day, ideas, specs, clusters, tags, publish ledger, and run logs over months of operation. Requirements:
- Machine queries: search, dedup, cross-linking, KPI aggregation
- Human readability: browsable, diffable, publishable
- Backup: simple, no external DB server
- Scale: tens of thousands of records over years

## Decision

Use **SQLite** (`db/engine.db`) as the machine source of truth, and **Markdown files** (`data/`, `publish/`) as the human source of truth. Every artifact is written to both.

## Consequences

### Positive
- SQLite: zero-config, single file, git-committable, full SQL (FTS5 for search)
- Markdown: human-readable, diffable, publishable directly to GitHub Pages
- Both can be rebuilt from each other if one is lost
- No external DB server to manage

### Negative
- SQLite file grows unboundedly (mitigated by WAL cleanup)
- Two sources of truth requires sync logic (handled by `store/` module)
- Not suitable for concurrent multi-writer (acceptable: single pipeline process)

### Neutral
- Binary DB in git (small, acceptable for this scale)

## Alternatives Considered

| Alternative | Pros | Cons | Why rejected |
|-------------|------|------|--------------|
| PostgreSQL | Concurrent, full-featured | Requires server, overkill for single-process | Too heavy for Phase 0-2 |
| DuckDB | Analytical queries | Less mature ecosystem, no FTS5 | No clear analytical need yet |
| JSON files only | Simple, human-readable | No SQL queries, slow full scans | Can't support KPI/queries at scale |

## Compliance

- [x] Data is truth — all data comes from fetches, no invention
- [x] Validation before publication — validate/ gate before publish/
- [x] Secrets only in .env — DB has no secrets
- [x] Markdown + index — all artifacts mirrored to MD

## References

- `plan.md` § Ключевые решения #2
- `src/engine/store/db.py`
- `src/engine/store/__init__.py`
