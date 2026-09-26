# ADR-004: Multi-level Markdown index architecture

**Date**: 2026-09-24
**Status**: Accepted
**Deciders**: Owner
**Consulted**: Agent

## Context

Constitution §3: "всё в Markdown, всё индексируется (глобальный → день → категория → кластер → тег → идея)." Spec #9: "многоуровневые MD-индексы (в т.ч. свой INDEX.md на каждую идею) + SQLite + перелинковка." The user explicitly requested "свой индекс создавать для каждой идеи."

## Decision

Build a **5-level Markdown index hierarchy**:
1. `index/INDEX.md` — global (statistics, recent ideas, clusters, tags, days, navigation)
2. `index/days/{date}.md` — per-day (items fetched, ideas generated)
3. `index/clusters/cluster_{id}.md` — per-cluster (items in cluster)
4. `index/tags/tag_{name}.md` — per-tag (ideas with this tag)
5. `index/ideas/idea_{id}.md` — per-idea (specs, bundles, tags, related ideas)

Plus `publish/en/INDEX.md` — public site index.

Cross-linking via `related_links` table (similar/cluster/source/spec relations).

## Consequences

### Positive
- Every artifact has a navigable path from global to specific
- Per-idea index shows full context: specs, bundles, tags, related
- Works as static site navigation (no server needed)
- Rebuildable from SQLite at any time

### Negative
- Index files grow with content (mitigated by per-day splits)
- Rebuild takes time at scale (incremental rebuild possible later)
- 5 levels may be deep for small datasets

### Neutral
- Built by `index/` module after every pipeline run
- Can be rebuilt via `build-index` CLI command

## Alternatives Considered

| Alternative | Pros | Cons | Why rejected |
|-------------|------|------|--------------|
| Single INDEX.md | Simple | Becomes huge, unusable at scale | Fails at 1000+ items |
| SQLite only (no MD indexes) | Fast queries | Not human-readable, not publishable | Violates "everything in MD" |
| Category only (no cluster/tag) | Simpler | Loses cross-cutting views | Spec requires cluster/tag levels |

## Compliance

- [x] Data is truth — indexes built from DB, no invention
- [x] Validation before publication — index files validated separately
- [x] Secrets only in .env — indexes contain no secrets
- [x] Markdown + index — this IS the index system

## References

- `constitution.md` § 3
- `spec.md` § Функциональные требования #9
- `research/github-repo-for-daily-research-2026-08-13.md` § 5 (Индексы)
- `src/engine/index/__init__.py`
