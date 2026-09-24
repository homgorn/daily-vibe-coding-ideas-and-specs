# AGENTS.md

Instructions for any AI coding agent or IDE working in this repository.

## Project in one paragraph

A daily research engine for vibe-coding: every day it fetches 30+ fresh features/projects/startups/top GitHub repos (+ news + user-ingested material), synthesizes them into ideas with viability scores, and produces hyper-detailed, agent-ready specs (Spec Kit + BMAD hybrid). Each idea gets a full content bundle: prompts, marketing kit, investor kit, ads, visuals, video clips, course lesson. Everything is stored as Markdown, indexed in multi-level MD indexes and SQLite, validated, and published through the Publish Ledger to GitHub Pages / Cloudflare Pages and (later) WordPress, Telegram, social channels.

## Current Status (2026-08-13)

**Phase 0 — Bootstrap (in progress)**

Done:
- Repository structure, docs (README, AGENTS, constitution, spec, plan, tasks, TODO, ROADMAP, CHANGELOG)
- Engine skeleton: `src/engine/` modules + `src/cli.py` with subcommands (`run`, `status`, `crawl`, `service`)
- SQLite schema with 17 tables + migrations (`db/engine.db` committed as backup)
- Tests: 33 passing (structure, DB, config, secrets, robots.txt, sitemap, service docs, fetch fingerprint/dedup)
- Dashboard stub (`dashboard/index.html` + `data.json`)
- Crawl module: robots.txt (RFC 9309), sitemap parsing, reference site crawling → `crawled_pages` + `service_docs` (FTS5)
- Knowledge/services: `knowledge/services/` (INDEX.md, _TEMPLATE.md, github.md) + indexer
- Config: `config.yaml` (sources, models, publish channels, crawl, knowledge, cache, schedule)
- `.env.example` with all required keys (GITHUB_TOKEN mandatory for fetch)

Next (Phase 0 exit criteria):
- `git init` + push to GitHub (public repo `daily-vibe-coding-ideas-and-specs`)
- Vendor frameworks as submodules: `frameworks/spec-kit`, `frameworks/bmad-method`
- Add `GITHUB_TOKEN` to `.env` → live fetch test (`python src/cli.py run` works on real data)

## Before you start

1. Read `constitution.md` — non-negotiable project rules.
2. Check `TODO.md` and `ROADMAP.md` for current status; never duplicate planned work.
3. Report status: if a session starts without an explicit task, open with current project status (Phase, last milestone, next step).
4. Run tests before committing: `python -m pytest tests/ -q`.

## Hard rules

- **Never** commit `.env` or any secret. Run `tests/test_secrets.py` if in doubt.
- **Never** invent data: star counts, dates, quotes, URLs must come from fetched data. Every claim cites a source (`Cited:` block).
- **Never** publish an artifact that failed validation (5 agents in `src/engine/validate/`).
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
- Output files: `outputs/` is not used — artifacts go to their typed folders (`publish/`, `knowledge/`, `data/`).
- Fingerprint for dedupe: `sha256(source|lower(title)|lower(url).rstrip('/'))` — see `src/engine/fetch/__init__.py:31`.

## Commands

```bash
python src/cli.py run            # full pipeline run (fetch → synthesize → spec → validate → index → report)
python src/cli.py status         # pipeline/ledger status summary
python src/cli.py crawl <url>    # crawl reference site (robots + sitemap)
python src/cli.py service index  # index knowledge/services/ to DB
python -m pytest tests/ -q       # run all tests
```

Not yet implemented (Phase 1+): `add-idea`, `build-index`, `dashboard`.

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

- **Config loading**: `src/engine/config.py` loads `config.yaml` + `.env`; use `secret(key)` for secrets.
- **DB**: `src/engine/store/db.py` — `init_db()` applies migrations; 17 tables including `items`, `ideas`, `specs`, `clusters`, `tags`, `related_links`, `publish_ledger`, `run_logs`, `llm_cache`, `crawled_pages`, `service_docs` (FTS5).
- **Fetch**: `src/engine/fetch/__init__.py` — GitHub search API (topics: vibe-coding, ai-agents, llm, mcp, ai-tools), Hacker News topstories, fingerprint dedupe, `store_items()` writes to `items` + `mentions`.
- **Crawl**: `src/engine/crawl/` — robots.txt parser (longest-match, crawl-delay), sitemap index + gz support, polite crawl with fallback paths.
- **Knowledge**: `src/engine/knowledge/` — indexes `knowledge/services/*.md` to `service_docs` + FTS5 for search.
- **CLI**: `src/cli.py` — single entry point with argparse subcommands; `run` logs to `run_logs` table.
- **Tests**: `tests/` — pytest, no network required (uses tmp DB). Run before commit.

## Common pitfalls to avoid

- Forgetting `GITHUB_TOKEN` in `.env` → fetch hits 60 req/h limit, fails "≥30 items/day" metric.
- Not normalizing URLs in fingerprint (trailing slash) → duplicate items across runs.
- Committing `.env` or `logs/raw/` — both gitignored for a reason.
- Using Cyrillic filenames — breaks tooling on some systems.
- Skipping tests before commit — CI will fail.