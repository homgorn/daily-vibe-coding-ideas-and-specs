# TODO

Текущие задачи. Сверять с ROADMAP.md (фазы) — здесь операционные пункты, там — стратегические.

## Фаза 0 — бутстрап (ЗАВЕРШЕНА)

- [x] Структура репозитория + git + GitHub
- [x] Документ-комплект (README/AGENTS/docs/spec-артефакты)
- [x] Скелет движка с модулями-заглушками
- [x] SQLite + миграции (17 таблиц)
- [x] Тесты pytest (структура, БД, конфиг, секреты) — **67 тестов**
- [x] Dashboard-заглушка
- [x] Первый research-артефакт (Spec Kit/BMAD/конкуренты/рынок)
- [x] Краулинг: robots.txt + sitemap + reference sites
- [x] Knowledge/services: карточки сервисов + FTS5
- [x] Исправлен fingerprint dedupe (URL trailing slash)
- [x] Исправлены кириллические имена файлов
- [ ] Git-репо на GitHub (public) + push
- [ ] Вендоринг frameworks (submodules spec-kit, BMAD-METHOD)
- [ ] GITHUB_TOKEN → живой fetch-тест GitHub trending

## Фаза 1 — обкатка пайплайна (14 дней seeding)

### Реализовано (2026-09-24):
- [x] LLM provider abstraction (`providers/`): кэш, маршрутизация по стадиям, mock
- [x] Fetch: GitHub + HN + RSS + npm + Reddit (дедуп fingerprint, mentions)
- [x] News: RSS news feeds → news_items → analyze → ideas (TechCrunch/Verge/Ars/HN/AI)
- [x] Synthesize: кластеризация (LLM + fallback) → идеи → Viability Score
- [x] Spec: генератор спеков (Spec Kit + BMAD структура + launch-команды IDE)
- [x] Validate: 8 агентов (data/text/image/video/post/seo_geo/links/legal)
- [x] Ingest: inbox.md + candidates/ + manual/ парсинг + add-idea CLI
- [x] Index: многоуровневый MD-индекс (global → day → cluster → tag → idea) + publish index
- [x] Store: MD-зеркала (data/ + publish/) для всех артефактов
- [x] Dashboard: data.json генератор из БД
- [x] CLI: полный пайплайн `run` (fetch → news → ingest → synthesize → spec → validate → index)
- [x] CLI: `validate --path/--dir`, `build-index`, `add-idea`, `dashboard`
- [x] SDD-структура: 5 ADR + шаблон в docs/10-decisions/

### Осталось:
- [ ] Реальный LLM вызов (вместо mock) — настроить OpenRouter/OpenAI ключ
- [ ] Product Hunt fetch (нужен ключ)
- [x] News: парсинг новостей → анализ → идеи
- [ ] LLM-кэш: hash промпта → ответ (структура есть, нужен реальный провайдер)
- [ ] KPI-таблица и первый weekly-отчёт
- [x] Интеграционный тест полного пайплайна (без сети) — `tests/test_pipeline.py`
- [ ] Реальный `site.base_url` в `config.yaml` (сейчас плейсхолдер `https://example.com` — sitemap/canonical/robots публикуют его)
- [ ] Коммит `src/cli.py` + всех новых файлов в git (после восстановления не закоммичено)

### Реализовано (2026-09-25, вторая сессия):
- [x] Восстановлен `src/cli.py` (инцидент: уничтожены переводы строк; реконструкция `recover_cli.py`, `ast.parse` OK)
- [x] `src/cli.py` переписан начисто после восстановления (17 однострочных suite'ов, 32 длинные строки), доказана AST-эквивалентность
- [x] CLI: фаза `[8/8] SITE` в `run` + команда `build-site` (static HTML → `site/`, broken_links=0)
- [x] GitHub Pages: `.github/workflows/pages.yml` (build-site → deploy-pages), `site/` в `.gitignore`
- [x] `tests/test_site.py` + `tests/test_dashboard.py` — ссылочная целостность и отсутствие локальных путей (+3 → **79 тестов**)
- [x] Исправлены битые ссылки листингов `ideas/` и `specs/` в `site.py`
- [x] Утечка абсолютных путей в `dashboard/data.json` и `site/` устранена (relativize + санитайзер)
- [x] ASCII-имена файлов: `store.safe_name()` + миграция 8 файлов (`tools/fix_ascii_filenames.py`)
- [x] `index/`: подчистка устаревших страниц + относительные ссылки вместо абсолютных

## Фаза 2 — публикации и боты

- [ ] Модуль publish: Publish Ledger, WordPress (REST), Cloudflare Pages (GitHub Pages готов: `pages.yml` + `site.py`)
- [ ] Модуль media: карточки HTML→PNG, карусели, OG, обложки
- [ ] Модуль notify: owner-бот отчёты + напоминания
- [ ] Модуль bots: owner-бот TG (статусы, ingest)
- [ ] Модуль email: IMAP-ингест + OCR
- [ ] Сайт: Cloudflare Pages (GitHub Pages уже работает через `site.py`)
- [ ] PWA: manifest + Service Worker + offline-кэш
- [ ] Web Push (VAPID)
- [ ] KPI weekly-отчёт
- [ ] Дашборд: полный функционал (лента, pipeline, рейтинги, форма идеи)
- [ ] Решения по авторам (персоны/бренд), About/Methodology

## Фаза 3 — видео и соцсети

- [ ] Видео-модуль: YouTube + TikTok (HyperFrames)
- [ ] Формат-матрица видео (9:16/16:9/1:1)
- [ ] X/Reddit/Quora (ручные пакеты)
- [ ] Мультиязычность видео (TTS, субтитры)

## Фаза 4 — реклама и масштабирование

- [ ] Meta Ads MCP пайплайн
- [ ] Авто-постинг картинок/каруселей
- [ ] Affiliate-мост, оферта Launch Kits (Lite/Standard/Premium)

## Фаза 5 — долгосрочное

- [ ] IPFS/Arweave публикация
- [ ] Зеркала на уникальных доменах
- [ ] API-доступ к спекам (B2B), marketplace
- [ ] Community-канал, Mentor-агент
