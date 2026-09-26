# ADR-003: 8-agent validation gate before publication

**Date**: 2026-09-24
**Status**: Accepted
**Deciders**: Owner
**Consulted**: Agent

## Context

Constitution §3 requires: "Публикуется только то, что прошло все 5 валидационных агентов + SEO/GEO-чекер + legal-check." The spec calls for publication only after all green checks. Original design had 5 agents; research and constitution require additional SEO/GEO and legal checks.

## Decision

Implement **8 validation agents** as a gate before any artifact reaches `publish/`:
1. **data** — citations present, no invented figures, viability score in range
2. **text** — frontmatter complete (title/tags/origin/viability_score), heading hierarchy, no placeholders
3. **image** — image references exist, og_image present
4. **video** — video references (for video artifacts)
5. **post** — social media constraints (Twitter 280, description 120-160)
6. **seo_geo** — title ≤60, description 120-160, single H1, FAQ block, JSON-LD
7. **links** — all external links alive (online check optional)
8. **legal** — investment disclaimers, AI disclosure, CC BY-NC-ND, BMAD trademark

## Consequences

### Positive
- Catches broken links, missing citations, SEO violations before publication
- Legal compliance (GDPR, EU AI Act, FTC) enforced automatically
- Machine-readable validation report for audit trail
- Constitution compliance is code, not just policy

### Negative
- Slower publication pipeline (8 checks per artifact)
- Link checking requires network (offline mode available)
- May produce false positives on edge cases (warnings vs errors)

### Neutral
- Validation runs in `run` pipeline phase 5
- Can be run standalone via `validate --path/--dir`

## Alternatives Considered

| Alternative | Pros | Cons | Why rejected |
|-------------|------|------|--------------|
| 5 agents only (original spec) | Faster, simpler | Missing SEO/legal required by constitution | Constitution violation |
| Manual review only | Human judgment | Not automatable, slow, inconsistent | Fails automation requirement |
| Single "quality" agent | Simple | Can't specialize per concern | Lower detection rate |

## Compliance

- [x] Data is truth — data agent checks citations
- [x] Validation before publication — this IS the validation
- [x] Secrets only in .env — no secrets checked in content
- [x] Markdown + index — validates MD frontmatter

## References

- `constitution.md` § 3
- `spec.md` § Функциональные требования #7
- `src/engine/validate/__init__.py`
