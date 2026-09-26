# AGENTS.md

Instructions for any AI coding agent or IDE working in this repository.

## Project in one paragraph

A daily research engine for vibe-coding: every day it fetches 30+ fresh features/projects/startups/top GitHub repos (+ news + user-ingested material), synthesizes them into ideas with viability scores, and produces hyper-detailed, agent-ready specs (Spec Kit + BMAD hybrid). Each idea gets a full content bundle: prompts, marketing kit, investor kit, ads, visuals, video clips, course lesson. Everything is stored as Markdown, indexed in multi-level MD indexes and SQLite, validated, and published through the Publish Ledger to GitHub Pages / Cloudflare Pages and (later) WordPress, Telegram, social channels.

## Current Status (2026-09-25)

**Phase 1 — Pipeline (in progress)**

Done:
- Full pipeline: `fetch → news → ingest → synthesize → spec → validate → index → site` (8 phases, all implemented)
- **79 tests passing** (structure, DB, config, secrets, robots, sitemap, fetch, news, validate, index, ingest, pipeline, site, dashboard)
- CLI: `run`, `status`, `validate`, `build-index`, `add-idea`, `dashboard`, `crawl`, `service`, `build-site`
- GitHub Pages deploy workflow: `.github/workflows/pages.yml` (builds `site/`, broken_links=0)
- Incident 2026-09-25: `src/cli.py` was destroyed (all newlines stripped), reconstructed by `recover_cli.py`, then rewritten clean with AST-equivalence proof
- All Phase 1 core modules implemented (see "Key implementation details")
- Config: `config.yaml` + `.env.example` complete
- Dashboard: `dashboard/data.json` generator (relative paths only, no local leaks)
- SDD structure: 5 ADRs + template in `docs/10-decisions/`

Next (Phase 1 exit criteria):
- Real LLM provider (replace mock with OpenRouter/OpenAI key)
- Live fetch test with `GITHUB_TOKEN`
- Real `site.base_url` in `config.yaml` (currently `https://example.com` placeholder)
- 14 days of daily runs (`python src/cli.py run`)

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
- **Spec**: `src/engine/spec/__init__.py` — Spec Kit + BMAD hybrid spec generator. Generates 12 sections: problem, solution, target_user, features, tech_stack, data_model, api, ui_ux, monetization, risks, launch_checklist, cited_sources. Appends launch commands for Claude Code, OpenCode, Codex, Cursor, Antigravity.
- **Validate**: `src/engine/validate/__init__.py` — 8 agents: data (citations), text (frontmatter/structure), image, video, post, seo_geo (title/desc/H1/FAQ/JSON-LD), links (online check optional), legal (disclaimers/trademark).
- **Ingest**: `src/engine/ingest/__init__.py` — parses `ingest/inbox.md`, `candidates/*.md`, `manual/*.md`. Interactive `add_idea_interactive()`.
- **Index**: `src/engine/index/__init__.py` — multi-level MD: `index/INDEX.md` (global), `index/days/`, `index/clusters/`, `index/tags/`, `index/ideas/idea_{id}.md` (per-idea with related). Also `publish/en/INDEX.md`. Stale pages are pruned by `_prune()`; links are repo-relative via `_rel_link()` (never absolute paths).
- **Store**: `src/engine/store/__init__.py` — MD mirrors to `data/YYYY-MM-DD/` and `publish/en/`. Functions: `write_raw_items`, `write_note`, `write_spec`, `write_idea`, `write_ranking`, `write_course_lesson`. `safe_name()` is the ONLY way to build filename stems (ASCII, sha1 fallback).
- **Providers**: `src/engine/providers/__init__.py` — LLM abstraction with SQLite cache (`db/llm_cache.sqlite`), model routing by stage (cheap/medium/expensive). Mock provider by default; OpenRouter ready when key set.
- **Site**: `src/engine/publish/site.py` — static HTML generator (`site/`): ideas/specs pages, RSS, sitemap, robots, dashboard copy; `_check_internal_links()` must return 0 broken before publish.
- **CLI**: `src/cli.py` — single entry point. `run` executes 8-phase pipeline (fetch → news → ingest → synthesize → spec → validate → index → site) with KPI check.

## Common pitfalls to avoid

- Forgetting `GITHUB_TOKEN` in `.env` → fetch hits 60 req/h limit, fails "≥30 items/day" metric.
- Not normalizing URLs in fingerprint (trailing slash) → duplicate items across runs.
- `str.isalnum()` is True for CJK/Cyrillic → never build filenames by hand; use `store.safe_name()`.
- Never put `DB_PATH`-style absolute paths into published artifacts (`data.json`, MD indexes) — use `_rel_path`/`_rel_link`.
- Stale generated files accumulate silently: `index/` is pruned on each build, but new artifact dirs must be pruned too.
- Committing `.env` or `logs/raw/` — both gitignored for a reason.
- Using Cyrillic filenames — breaks tooling on some systems.
- Skipping tests before commit — CI will fail.
- Publishing without validation — `validate` must pass before any artifact goes to `publish/`.
- Writing to `outputs/` — this directory is not used; artifacts go to typed folders (`publish/`, `knowledge/`, `data/`).
