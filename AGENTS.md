# AGENTS.md

Instructions for any AI coding agent or IDE working in this repository.

## Project in one paragraph

A daily research engine for vibe-coding: every day it fetches 30+ fresh features/projects/startups/top GitHub repos (+ news + user-ingested material), synthesizes them into ideas with viability scores, and produces hyper-detailed, agent-ready specs (Spec Kit + BMAD hybrid). Each idea gets a full content bundle: prompts, marketing kit, investor kit, ads, visuals, video clips, course lesson. Everything is stored as Markdown, indexed in multi-level MD indexes and SQLite, validated, and published through the Publish Ledger to GitHub Pages / Cloudflare Pages and (later) WordPress, Telegram, social channels.

## Current Status (2026-09-27)

**Phase 1 — Pipeline (live, OpenRouter free-tier)**

Done:
- Full pipeline: `fetch → news → ingest → synthesize → spec → validate → index → site` (8 phases)
- **79 tests passing**, all offline (network is blocked in tests via `tests/conftest.py`)
- CLI: `run`, `status`, `validate`, `build-index`, `add-idea`, `dashboard`, `build-site`, `crawl`, `service`
- GitHub Pages workflow `.github/workflows/pages.yml`; remote `github.com/homgorn/daily-vibe-coding-ideas-and-specs`
- **Live LLM via OpenRouter** — `models.provider: openrouter`, free-tier models with automatic fallbacks
- Per-stage `max_tokens` + time budgets (`models.budget_minutes`) so free-tier queues can't hang a run
- Incident 2026-09-25: `src/cli.py` was destroyed (newlines stripped), reconstructed and rewritten
- Incident 2026-09-27: `test_pipeline.py` claimed "offline" but hit the real LLM; now forced to mock + network guard added
- 5 ADRs in `docs/10-decisions/`

Next (Phase 1 exit criteria):
- **Valid `GITHUB_TOKEN`** in `.env` (the one provided returned `Bad credentials`) — needed for the ≥30 items/day KPI
- Enable GitHub Pages in repo settings so `site.base_url` resolves
- 14 consecutive days of daily runs

## Before you start

1. Read `constitution.md` — non-negotiable project rules.
2. Check `TODO.md` and `ROADMAP.md` for current status; never duplicate planned work.
3. Report status: if a session starts without an explicit task, open with current project status (Phase, last milestone, next step).
4. Run tests before committing: `python -m pytest tests/ -q`.

## Hard rules

- **Never** commit `.env` or any secret. Run `tests/test_secrets.py` if in doubt.
- **Never** invent data: star counts, dates, quotes, URLs must come from fetched data. Every claim cites a source (`Cited:` block).
- **Never** publish an artifact that failed validation (8 agents in `src/engine/validate/`).
- **Never** copy third-party content verbatim — rewrite in own words + original link (license CC BY-NC-ND 4.0 applies to our content).
- **Never** let template filler pass as analysis. A spec whose generation failed carries `FALLBACK_MARKER` and the validator rejects it. A spec that reads like a real one but says "See summary above" is worse than no spec, because downstream nothing can tell them apart.
- No comments in code unless asked. Code stays clean, modular, tested.
- Every change: update `CHANGELOG.md`. Every decision: ADR in `docs/10-decisions/`.
- Everything saved as Markdown; everything indexed in MD indexes (global → day → category → cluster → tag → idea).
- Filenames: ASCII only (no Cyrillic).

## Conventions

- Internal docs and logs: Russian. Public artifacts (README, publish/): English.
- Days are stored in `data/YYYY-MM-DD/{raw,notes,specs,prompts}/`.
- Idea lifecycle: `new → watching → spec → shipped → dead`; status lives in the artifact frontmatter and DB.
- Every idea needs frontmatter: `tags`, `related`, `origin: research|user|news|ingest`, `viability_score`.
- Fingerprint for dedupe: `sha256(source|lower(title)|lower(url).rstrip('/'))` — see `src/engine/fetch/__init__.py:31`.
- Run tests before committing: `python -m pytest tests/ -q`.

## Commands

```bash
python src/cli.py run            # full pipeline: fetch → news → ingest → synthesize → spec → validate → index → site
python src/cli.py status         # pipeline/ledger status + KPI
python src/cli.py validate --path FILE    # validate single artifact
python src/cli.py validate --dir DIR      # validate all .md in directory
python src/cli.py build-index    # rebuild all MD indexes
python src/cli.py add-idea       # interactive manual idea entry
python src/cli.py dashboard      # regenerate dashboard/data.json
python src/cli.py build-site     # build static HTML site (site/, GitHub Pages)
python src/cli.py crawl <url>    # crawl reference site (robots + sitemap)
python src/cli.py service index  # index knowledge/services/ to DB
python -m pytest tests/ -q       # run all tests (79)
```

## Where things live

- `src/engine/` — pipeline modules (fetch, news, ingest, store, synthesize, spec, media, validate, publish, index, notify, courses, bots, providers, email, domains, crawl, knowledge)
- `frameworks/` — vendored Spec Kit + BMAD (git submodules, updated weekly)
- `research/` — deep research artifacts (MD, ASCII filenames)
- `ingest/` — drop zone for user manual input (`inbox.md`)
- `logs/` — run/chat/publish logs (raw versions gitignored)
- `dashboard/` — static dashboard (index.html + data.json)
- `db/engine.db` — SQLite (committed as backup; journal/wal gitignored)
- `knowledge/services/` — reference service cards (INDEX.md, _TEMPLATE.md, github.md)
- `docs/legal/` — compliance checklist, must pass before public publishing
- `config.yaml` — all non-secret configuration
- `.env` — secrets (never committed; template in `.env.example`)

## Key implementation details (verified)

- **Config**: `src/engine/config.py` loads `config.yaml` + `.env`; use `secret(key)` for secrets.
- **DB**: `src/engine/store/db.py` — `init_db()` applies migrations; 17 tables including `items`, `ideas`, `specs`, `clusters`, `tags`, `related_links`, `publish_ledger`, `run_logs`, `llm_cache`, `crawled_pages`, `service_docs` (FTS5).
- **Fetch**: `src/engine/fetch/__init__.py` — GitHub search API (topics: vibe-coding, ai-agents, llm, mcp, ai-tools), Hacker News topstories, RSS blogs, npm weekly, Reddit RSS. Fingerprint dedupe. `store_items()` writes to `items` + `mentions`.
- **News**: `src/engine/news/__init__.py` — RSS news feeds (TechCrunch, Verge, Ars Technica, HN Best, AI News) → `news_items` table → analyze unprocessed → mark processed.
- **Synthesize**: `src/engine/synthesize/__init__.py` — LLM clustering (with source-based fallback) → idea synthesis → Viability Score (market/competition/time_to_mvp/risk/score/confidence 0-100).
- **Spec**: `src/engine/spec/__init__.py` — Spec Kit + BMAD hybrid spec generator. Sections are requested in **four separate calls** (`SPEC_GROUPS`: problem/solution/target_user/features, tech_stack/data_model, api/ui_ux, monetization/risks/launch_checklist/cited_sources). One 12-section request is not viable: the model wants >9.7k tokens and fails to parse even at `max_tokens=16000`, where it stops on its own, while small groups finish on their own and parse reliably. Group size follows the *longest* section, not the average — `tech_stack` and `api` emit large code blocks, so the four architecture sections are split 2+2 and would still truncate at `max_tokens=3200` as one group. A group that comes back unparseable (truncation) or answers only some keys is re-asked once, narrowed to the missing keys (`MAX_GROUP_ATTEMPTS = 2`) — never re-asks a section it already has. `extract_json_object()` strips code fences and prose and brace-scans for the outermost object. A failed group marks only its own sections `(not provided by model)` plus a `*Partial spec*` note; `FALLBACK_MARKER` appears only when **no** section was produced, so one lost call never discards 8 good ones. Prompts carry grounding rules: source materials only, no invented statistics/dates/quotes/versions/URLs. Launch commands for Claude Code, OpenCode, Codex, Cursor, Antigravity are appended by the template.
- **Spec regeneration tooling**: `tools/reset_fallback_specs.py` deletes incomplete specs using the same `spec_is_incomplete()` the pipeline uses, then `tools/regen_specs.py` rebuilds them. The pipeline itself already self-heals: `select_ideas_needing_specs()` picks up ideas with no spec row **or** an incomplete spec file, so a partial spec is retried on the next `run` instead of being permanent (ADR-008). `save_spec()` is idempotent, so retries never duplicate rows. `tools/check_spec_json.py` confirms a live model returns parseable JSON; `tools/audit_specs.py` reports real vs incomplete specs; `tools/audit_cache_keys.py` shows which JSON keys each cached call actually returned; `tools/diagnose_last_failure.py` separates truncation (unclosed brace) from a malformed payload; `tools/gen_one_spec.py` generates a single spec synchronously and prints section presence.
- **Validate**: `src/engine/validate/__init__.py` — 9 agents: data (citations), text (frontmatter/structure), image, video, post, seo_geo (title/desc/H1/FAQ/JSON-LD), links (online check optional), legal (disclaimers/trademark), **generation** (rejects any spec carrying `FALLBACK_MARKER`).
- **Ingest**: `src/engine/ingest/__init__.py` — parses `ingest/inbox.md`, `candidates/*.md`, `manual/*.md`. The inbox supports two shapes: the documented checkbox line `- [ ] <url> | <description>` (title derived from the URL slug) and a key/value block `## Title` / `URL:` / `Description:` / `tags:`. Instruction sections (`Правила`, `Rules`, `Формат`, archive) and placeholder lines are skipped, so the shipped template never manufactures ideas. Interactive `add_idea_interactive()`.
- **Index**: `src/engine/index/__init__.py` — multi-level MD: `index/INDEX.md` (global), `index/days/`, `index/clusters/`, `index/tags/`, `index/ideas/idea_{id}.md` (per-idea with related). Also `publish/en/INDEX.md`. Stale pages are pruned by `_prune()`; links are repo-relative via `_rel_link()` (never absolute paths).
- **Store**: `src/engine/store/__init__.py` — MD mirrors to `data/YYYY-MM-DD/` and `publish/en/`. Functions: `write_raw_items`, `write_note`, `write_spec`, `write_idea`, `write_ranking`, `write_course_lesson`. `safe_name()` is the ONLY way to build filename stems (ASCII, sha1 fallback).
- **Providers**: `src/engine/providers/__init__.py` — LLM abstraction with SQLite cache (`db/llm_cache.sqlite`), model routing by stage (cheap/medium/expensive) plus per-stage `fallbacks`. Active provider comes from `models.provider` (`mock` | `openrouter`). Free-tier queues are real, so `models.budget_minutes` caps LLM time per stage — when exhausted the stage returns `skipped_budget` instead of hanging. `models.max_tokens_by_stage` keeps requests small (big limits = minutes of queueing).
- **Model tooling**: `tools/check_models.py` (do the configured models answer?), `tools/bench_models.py` (latency + tok/s), `tools/probe_free_models.py` (find working free models). Free models churn — re-probe before blaming the code.
- **Site**: `src/engine/publish/site.py` — static HTML generator (`site/`): ideas/specs pages, RSS, sitemap, robots, dashboard copy; `_check_internal_links()` must return 0 broken before publish.
- **CLI**: `src/cli.py` — single entry point. `run` executes 8-phase pipeline (fetch → news → ingest → synthesize → spec → validate → index → site) with KPI check.

## Common pitfalls to avoid

- **A passing validation run can still be 100% garbage.** Until 2026-09-27 every spec in the repo was a fixed template: `json.loads` failed on the model's fenced JSON, the code fell back silently, and the validator scored 12/12 green. When a generated artifact looks plausible, read it. Silent fallbacks are the failure mode this project is built to avoid.
- **Tests must never touch the network.** A test that only mocks its own imports still hits the real LLM via `engine.providers`. `tests/conftest.py` blocks `socket.connect` session-wide, so a regression fails fast instead of hanging for 20 minutes. Integration tests set `cfg["models"]["provider"] = "mock"`.
- **Never assume a 4xx is transient.** `400 not a valid model ID` and `401` cannot be fixed by retrying; only 429 and 5xx can. A typo'd model ID used to burn the whole fallback chain four times over and surface as a timeout-shaped error.
- **Check `finish_reason` before blaming the parser.** `length` means truncation, `stop` means the model finished and the payload is genuinely malformed. Different fixes, and guessing costs a long benchmarking round-trip.
- **A cached response can outlive its usefulness.** Measured 2026-09-27: 30 of 85 cached OpenRouter responses were truncated, and because the cache served them back verbatim, every retry of a spec group got the identical broken text — `MAX_GROUP_ATTEMPTS` worked correctly and still recovered nothing. Any call that can be retried after a *bad* answer must pass `cache=False`, and the retry must send a different prompt, or the cache makes recovery impossible. Tests that mock `complete()` cannot catch this: the mock has no cache. `tools/prune_broken_cache.py` drops entries that never closed.
- **Free OpenRouter models are slow, not broken.** A `429 "temporarily rate-limited upstream"` means shared-pool queueing, not a bad key. Large `max_tokens` on a free model means minutes of queueing. Keep per-stage limits small and rely on `fallbacks`.
- `models.provider` is the switch between `mock` and `openrouter`. If it's missing, the registry silently falls back to mock — a green run proves nothing.
- Forgetting `GITHUB_TOKEN` in `.env` → fetch hits 60 req/h limit, fails "≥30 items/day" metric.
- Not normalizing URLs in fingerprint (trailing slash) → duplicate items across runs.
- `str.isalnum()` is True for CJK/Cyrillic → never build filenames by hand; use `store.safe_name()`.
- Never put `DB_PATH`-style absolute paths into published artifacts (`data.json`, MD indexes) — use `_rel_path`/`_rel_link`.
- A test asserting a secret is absent from a file must skip empty values: `"" in anything` is always `True`, so any blank `TOKEN=` line fails the assertion.
- Stale generated files accumulate silently: `index/` is pruned on each build, but new artifact dirs must be pruned too.
- Committing `.env` or `logs/raw/` — both gitignored for a reason.
- Using Cyrillic filenames — breaks tooling on some systems.
- Skipping tests before commit — CI will fail.
- Publishing without validation — `validate` must pass before any artifact goes to `publish/`.
- Writing to `outputs/` — this directory is not used; artifacts go to typed folders (`publish/`, `knowledge/`, `data/`).
