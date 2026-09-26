# ADR-002: Spec Kit + BMAD hybrid for spec generation

**Date**: 2026-08-13
**Status**: Accepted
**Deciders**: Owner
**Consulted**: Agent (deep research)

## Context

The project generates agent-ready specs. Two established frameworks exist:
- **Spec Kit** (github/spec-kit, 126K+ stars, MIT): Spec-Driven Development with constitution → spec → plan → tasks gates
- **BMAD-METHOD** (bmad-code-org, 51K+ stars, MIT + trademark): 21 agent roles (Analyst, PM, Architect, Dev, QA), story files, expansion packs

Research (konabos, reenbit, spec-compare) converges: Spec Kit is the standard for greenfield pipelines; BMAD provides depth in planning (PRD/architecture) and role templates.

## Decision

Use a **hybrid approach**: Spec Kit constitution + gates for structure, BMAD role templates + story format for content depth. Both frameworks vendored as git submodules under `frameworks/`.

## Consequences

### Positive
- Best of both: SDD rigor + role-based depth
- Community-validated patterns
- Both MIT-licensed (compatible)
- Submodules updatable weekly

### Negative
- Two frameworks to maintain/update
- BMAD™ trademark cannot be used in commercial project texts as our own
- Learning curve for both systems

### Neutral
- Hybrid requires custom glue code (`src/engine/spec/`)

## Alternatives Considered

| Alternative | Pros | Cons | Why rejected |
|-------------|------|------|--------------|
| Spec Kit only | Simpler, single framework | Less depth in role-based planning | Missing BMAD's PM/Architect depth |
| BMAD only | Rich roles | No SDD gate structure | Missing Spec Kit's constitution/gates |
| Custom spec format | Full control | No community validation, reinvent wheel | Higher risk, slower to validate |

## Compliance

- [x] Data is truth — specs cite fetched sources
- [x] Validation before publication — specs pass validate/ agents
- [x] Secrets only in .env — no secrets in spec templates
- [x] Markdown + index — specs written to data/ and publish/en/

## References

- `research/github-repo-for-daily-research-2026-08-13.md` (deep research results)
- `constitution.md` § 2 (BMAD trademark)
- `src/engine/spec/__init__.py`
