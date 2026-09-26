# Tasks — разбивка на задачи (Spec Kit)

Статусы: `[ ]` не начато, `[~]` в работе, `[x]` готово. Задачи Фазы 0 (текущая) и ближайшего продолжения.

## Фаза 0 — бутстрап [x] ЗАВЕРШЕНА

- [x] 0.1 Структура репозитория, .gitignore, .env.example, лицензии
- [x] 0.2 Документ-комплект (README/AGENTS/CHANGELOG/TODO/ROADMAP)
- [x] 0.3 Spec-артефакты (constitution/spec/plan/tasks)
- [x] 0.4 docs/ (12 документов + ADR-шаблон + 5 ADR)
- [x] 0.5 Скелет движка src/engine/* + src/cli.py
- [x] 0.6 SQLite + миграции + схема (17 таблиц)
- [x] 0.7 Тесты pytest (67)
- [x] 0.8 Dashboard-заглушка
- [x] 0.10 Git-репо на GitHub (public) + push
- [x] 0.11 Вендоринг frameworks (submodules spec-kit, BMAD-METHOD)
- [ ] 0.12 GITHUB_TOKEN → живой fetch-тест GitHub trending

## Фаза 1 — движок (обкатка) [~] В РАБОТЕ

### Готово (2026-09-24):
- [x] 1.1 fetch: GitHub + HN + RSS + npm + Reddit (дедуп, fingerprint, mentions)
- [x] 1.4 news: RSS news feeds → analyze → ideas (TechCrunch/Verge/Ars/HN/AI)
- [x] 1.6 synthesize: кластеры, дедуп, идеи, Viability Score (LLM + fallback)
- [x] 1.7 spec: генератор спеков + launch-команды (Spec Kit + BMAD hybrid)
- [x] 1.8 store: MD-зеркала + запись в БД (write_spec, write_idea, write_note...)
- [x] 1.9 index: многоуровневые индексы + перелинковка (global→day→cluster→tag→idea)
- [x] 1.10 validate: 8 агентов (data/text/image/video/post/seo_geo/links/legal)
- [x] 1.11 providers: LLM-абстракция + кэш + маршрутизация по стадиям
- [x] 1.12 ingest: inbox.md + candidates + manual + add-idea CLI
- [x] CLI: полный пайплайн run() + validate + build-index + dashboard
- [x] SDD: 5 ADR + шаблон

### Готово (2026-09-25):
- [x] Инцидент: восстановлен `src/cli.py` (уничтожены переводы строк; реконструкция `recover_cli.py`) + чистый рефакторинг с доказательством AST-эквивалентности (79 тестов зелёные)
- [x] CLI: фаза `[8/8] SITE` в run + команда `build-site` (static HTML → `site/`)
- [x] site: ссылочная целостность листингов (broken_links 12→0), санитайзер локальных путей, `tests/test_site.py`
- [x] GitHub Pages: `.github/workflows/pages.yml` (build-site → deploy-pages), `site/` в `.gitignore`
- [x] Хайгиена данных: ASCII-имена файлов (`store.safe_name()` + `tools/fix_ascii_filenames.py`), относительные пути в `dashboard/data.json` и MD-индексах, подчистка устаревших index-страниц

### Осталось:
- [ ] 1.5 email/OCR: заглушка Phase 2
- [ ] 1.13 KPI-отчёт weekly
- [ ] 1.14 Реальный LLM (вместо mock) — ключ OpenRouter/OpenAI
- [ ] 1.15 Live fetch test с GITHUB_TOKEN
- [x] 1.16 Интеграционный тест полного пайплайна — `tests/test_pipeline.py` (offline, 2 теста)

## Фаза 2 — публикации [ ] Phase 2

- [ ] 2.1 publish/ledger.py + адаптеры (wp/tg/github-pages/cf-pages/linkedin/bluesky/vk)
- [ ] 2.2 bots/ — owner-бот (статусы, напоминания, ingest)
- [ ] 2.3 media/ — карточки/карусели/OG (HTML→PNG)
- [ ] 2.4 email/ — IMAP-ингест + OCR
- [ ] 2.5 сайт: Cloudflare Pages-деплой (GH Pages уже работает: `site.py` + `pages.yml`)
- [ ] 2.5.1 PWA (manifest + Service Worker + offline) + Web Push (VAPID)
- [ ] 2.6 courses/ — первый курс
- [ ] 2.7 dashboard — полный функционал
