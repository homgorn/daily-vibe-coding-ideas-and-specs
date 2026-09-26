# CHANGELOG

Формат: дата — что изменилось — кем (bot/agent/user). Правило: **каждый** коммит, меняющий поведение или контент, добавляет запись здесь.

## 2026-09-25 (3) — Самокритика восстановления: рефакторинг cli.py, утечка путей, ASCII-имена, подчистка индексов

### Самокритика (что оказалось плохо после восстановления)
- `src/cli.py` был функционально цел, но в нечитаемом виде: **17 однострочных `if/for: stmt`**, ни одной пустой строки между top-level `def`, 32 строки >120 символов, слипшийся доктринг (538 символов), тела вложенных блоков с отступом 138 пробелов
- Переписан начисто; эквивалентность доказана **поперным сравнением `ast.dump`**: 9/10 функций побайтово-AST идентичны, отличия только в `cmd_dashboard` (3 намеренных правки, перечислены ниже)
- Утечка: `dashboard/data.json` (и его копия в `site/`) содержал абсолютные пути `G:\ЗАКАЗЧИКИ\...` — публиковался наружу
- Нарушение хард-рула «ASCII filenames»: 8 файлов в `publish/` и `data/` с CJK/кириллицей в имени (`str.isalnum()` считает их буквами)
- `index/` содержал **устаревшие страницы** удалённых сущностей (15 idea-страниц при 9 идеях, 11 cluster-страниц при 4 кластерах) и абсолютные пути в ссылках на спеки

### Исправления
- **`store.safe_name()`**: NFKD + ASCII-транслитерация; нелатинные заголовки → стабильный sha1-суффикс; применено во всех 5 писателях (`write_note/spec/idea/ranking/course_lesson`)
- **`tools/fix_ascii_filenames.py`** (идемпотентный, dry-run по умолчанию): переименовано 8 файлов, обновлено 2 строки `specs.path` в БД, не-ASCII имён не осталось
- **`index/_prune()` + `_prune_days()`**: удаляются index-страницы для сущностей, которых больше нет в БД (дни — только без единого item, без потерь); в `results` добавлен ключ `pruned`
- **`index/_rel_link()`**: ссылки на спеки/бандлы в `index/ideas/*` — repo-relative POSIX вместо абсолютных путей; отсутствующие файлы помечаются `(file missing)` вместо битой ссылки
- **`cmd_dashboard`**: пути спеков relativize'ятся относительно ROOT (`_rel_path`), наружу уходит `data/2026-09-25/specs/10_F-Droid-2-0.md`
- **`site._sanitize_public_json()`**: копия `dashboard/data.json` в `site/` чистится от любых строк вида `C:\...`/`C:/...` (защита в два слоя)

### Новое
- **`tests/test_dashboard.py`** (2 теста): относительные пути в data.json + fallback `_rel_path`
- **`tests/test_site.py`** +1 тест: в собранном сайте не должно быть локальных абсолютных путей
- `.github/workflows/pages.yml` проверен: yaml валиден, jobs `build`+`deploy`, триггеры `push`/`workflow_dispatch`

### Верификация
- **79 тестов** проходят (+dashboard 2, +site 1)
- **Run #15**: fetch=9, ideas=3, validation **9/9 green**, indexes=20, **site pages=23, broken_links=0**
- Аудит `site/`: 249 локальных ссылок — **0 битых**, 19 JSON-LD — все валидны, утечек путей нет, `<title>`/`<h1>` на всех 23 страницах
- Аудит `index/` + `publish/en/INDEX.md`: **0 абсолютных и 0 битых** md-ссылок
- `PRAGMA integrity_check` = ok, `foreign_key_check` = пусто
- Смок всех команд CLI: `status`, `build-index`, `dashboard`, `build-site`, `service index|list`, `validate --dir` (идеи 6/6, спеки 6/6)

## 2026-09-25 (2) — Восстановление cli.py, фаза [8/8] SITE, GitHub Pages

### Инцидент и восстановление
- **`src/cli.py` был уничтожен** (все переводы строк удалены, UTF-8 BOM, 17770 байт без `\n`); HEAD-версия в git — старая Phase-0, непригодна
- Восстановлен алгоритмической реконструкцией переносов строк (`recover_cli.py`: сплит по кандидатам + `ast.parse`-валидация префиксами с закрытием открытых `try:`/`if:` блоков): **300 строк, `ast.parse` OK, все маркеры на месте**
- Починены 2 разорванных комментария `# noqa: E402`
- **Верификация**: `python src/cli.py status`, `--help`, полный `run` — работают

### Новое
- **Фаза `[8/8] SITE`** в `cmd_run`: `build_site()` → `results["site"]` (pages, broken_links) + строка в Summary
- **GitHub Pages**: `.github/workflows/pages.yml` (checkout → pip → `build-site` → deploy-pages)
- **`tests/test_site.py`**: 2 теста (ссылочная целостность листингов, пустой источник)
- `.gitignore`: `site/` (генерируется, не коммитится)

### Исправления
- **`site.py` битые ссылки 12→0**: листинги `ideas/index.html` и `specs/index.html` вели на `ideas/idea-…html` (двойной путь, страница же внутри `ideas/`) — href теперь относительный к каталогу листинга

### Верификация
- **76 тестов** проходят (+site 2)
- **Run #12**: fetch=29, news=80, ideas=3, validation **6/6 green**, indexes=16, **site pages=17, broken_links=0**

## 2026-09-25 — News-модуль, дедуп идемпотентность, интеграционные тесты, чистка данных

### Верификация
- **74 теста** проходят (+news 5, +pipeline 2)
- **Run #11**: fetch=12, news=92, ideas=3, validation **6/6 green**, indexes=16
- Интеграционный тест полного пайплайна offline (без сети, tmp-директории): `tests/test_pipeline.py`

### Новое
- **`news/` модуль**: RSS (TechCrunch/Verge/Ars/HN Best/AI News) → `news_items` → analyze → идеи; фаза 2/7 в `run`
- **Интеграционные тесты**: полный пайплайн offline (fake fetch/news, tmp DB+data+publish+index) + проверка дедупа между прогонами
- `.gitignore`: `db/llm_cache.sqlite`, `logs/publish/raw/`

### Исправления (критичные)
- **`load_idea` FK-баг**: `item_tags.item_id` ссылается на `items(id)`, а не `ideas(id)` — теги брались от случайного item; исправлено через `ideas.item_id` → `items` (+fallback по `source_url`) (`spec/__init__.py`)
- **`load_cluster_items` FK-баг**: `JOIN ideas i2 ON ic2.item_id = i2.id` (item id = idea id) — источники спеков брались от несуществующих связей; переписан join через `ideas.item_id/source_url`
- **Дедуп кластеров**: `save_clusters` создавал дубль кластера каждый прогон; теперь SELECT по name перед INSERT
- **Дедуп идей**: `save_ideas` плодил дубли каждый прогон; теперь дедуп по `source_url`; заполняется `ideas.item_id` (первый item кластера)
- **Локальные даты**: `created_at` в ideas/clusters теперь `datetime('now','localtime')` — согласовано с `mentions.day` (KPI «сегодня» больше не рассинхронен с UTC)
- **`write_spec` frontmatter**: добавлены `description`, `canonical`, `tags`; title усечён до 70 chars; экранирование кавычек
- **`write_idea`**: убрана лишняя кавычка в `status: ..."`, экранирование кавычек в title
- **`cli.py` stdout-guard**: rewrap в UTF-8 только для не-UTF-8 консоли — импорт `cli` больше не ломает pytest-capture
- **`init_db/get_conn`**: `db_path=None` резолвится в рантайме (патчабельно в тестах)
- **LLM cache**: `row_factory = Row` (было `TypeError: tuple indices...`)

### Чистка данных (one-off)
- Слиты дубли: **6 идей** (по source_url), **7 кластеров** (по name), specs перепривязаны, удалены **24 осиротевших файла**
- Итог: ideas 12→6, clusters 11→4, specs 12→6; все 6 спеков + 6 идей валидны (восстановлены и допатчены спеки 1–3: tags/description/canonical)
- Индексы пересобраны (sub-indexes 29→16 — без дублей)

### Инцидент
- **Run #10 завис** (сеть/блокировка DB), процесс убит, run помечен `failed`; после этого run#11 отработал за 55s

## 2026-09-24 — Фаза 1: полный пайплайн реализован и верифицирован

### Верификация
- **67 тестов** проходят
- **Полный пайплайн** `run` отработал: fetch → ingest → synthesize → spec → validate → index
- **KPI**: 144 items (✓ ≥30), 9 ideas (✓ ≥5), 9 specs, 6/6 validation passed
- Dashboard data.json сгенерирован

### Критика и исправления
- **Глубокая критика**: выявлено 13 критических пробелов между spec/plan/constitution и реализацией
- Исправлен **fingerprint dedupe bug**: URL trailing slash → дубли между прогонами (`fetch/__init__.py:31`)
- Исправлены **кириллические имена файлов**: `репа-на-github-...` → `github-repo-for-daily-research-...`
- Исправлен **SQLite row_factory** в LLM cache (tuple → Row)
- Исправлен **frontmatter write_spec**: добавлены tags, description, canonical

### SDD-структура
- `docs/10-decisions/_TEMPLATE.md` — ADR-шаблон
- `docs/10-decisions/ADR-001-sqlite-md-mirrors.md` — SQLite + Markdown mirrors
- `docs/10-decisions/ADR-002-spec-kit-bmad-hybrid.md` — Spec Kit + BMAD hybrid
- `docs/10-decisions/ADR-003-8-agent-validation.md` — 8-agent validation gate
- `docs/10-decisions/ADR-004-multilevel-md-index.md` — multi-level MD index
- `docs/10-decisions/ADR-005-llm-provider-abstraction.md` — LLM provider abstraction

### Новые модули (Phase 1 core)
- **`providers/`** — LLM abstraction: кэш (SQLite), маршрутизация cheap/medium/expensive, mock+OpenRouter
- **`fetch/`** — +RSS (Atom+RSS2.0), +npm weekly, +Reddit RSS; fingerprint dedupe + mentions
- **`news/`** — RSS news feeds (TechCrunch, Verge, Ars Technica, HN Best, AI News) → news_items → analyze → ideas
- **`synthesize/`** — кластеризация → идеи → Viability Score (market/competition/time_to_mvp/risk/score/confidence)
- **`spec/`** — генератор спеков: Spec Kit + BMAD структура (12 секций) + launch-команды для 5 IDE
- **`validate/`** — 8 агентов: data, text, image, video, post, seo_geo, links, legal
- **`ingest/`** — парсинг inbox.md + candidates/ + manual/, add-idea CLI
- **`index/`** — многоуровневый MD-индекс: global → day → cluster → tag → idea + publish index
- **`store/`** — MD-зеркала: write_raw_items, write_note, write_spec, write_idea, write_ranking, write_course_lesson

### CLI (переписан)
- `run` — полный пайплайн: fetch → news → ingest → synthesize → spec → validate → index (7 фаз, KPI-чек)
- `validate --path/--dir [--type] [--links]` — валидация артефактов
- `build-index` — пересборка всех MD-индексов
- `add-idea` — интерактивный ввод идеи
- `dashboard` — генерация dashboard/data.json из БД
- UTF-8 encoding fix для Windows console

### Тесты
- **72 теста** (было 33): +validate (15), +index (9), +ingest (9), +news (5), +fingerprint fix

## 2026-09-24 — Фаза 0: финализация бутстрапа

- Добавлен submodule `frameworks/spec-kit` (github/spec-kit)
- Добавлен submodule `frameworks/bmad-method` (bmad-code-org/BMAD-METHOD) в .gitmodules
- Все 33 теста pytest проходят (структура, БД, конфиг, секреты, robots.txt, sitemap, service_docs, fetch fingerprint/dedup)
- Модуль fetch: GitHub Search API (topics: vibe-coding, ai-agents, llm, mcp, ai-tools) + Hacker News topstories, fingerprint-дедуп, запись в items + mentions
- Обновлён AGENTS.md с текущим статусом, командами и ключевыми деталями реализации
- Обновлён TODO.md с отметками прогресса
- Готов к `git push` в GitHub (public repo `daily-vibe-coding-ideas-and-specs`)

## 2026-08-13 — Фаза 0: бутстрап проекта

- Создан репозиторий `daily-vibe-coding-ideas-and-specs` (public), структура папок
- Написан документ-комплект: README (EN), AGENTS.md, constitution.md, spec.md, plan.md, tasks.md
- docs/: architecture, data-model, pipeline, publishing, media-video, courses, runbook, glossary, user-guide, decisions, kpi, legal
- Скелет движка `src/engine/` (все модули-заглушки с интерфейсами) + `src/cli.py`
- SQLite: схема БД + миграции (schema_migrations)
- Тесты pytest: структура, БД, конфиг, секреты
- Dashboard-заглушка (index.html + генератор data.json)
- Первый research-артефакт: рисёрч Spec Kit / BMAD / конкуренты / рынок
- Лицензии: контент CC BY-NC-ND 4.0, код AGPL-3.0
- TODO.md, ROADMAP.md, config.yaml, .env.example, .gitignore

## 2026-08-13 — Модуль crawl + knowledge (карточки сервисов) + PWA в планах

- Новый модуль `src/engine/crawl/`: парсер robots.txt (RFC 9309, longest-match, crawl-delay, sitemap-подсказки), парсер sitemap (XML/gz/sitemapindex +1 уровень), честный краулинг с фолбэком на стандартные sitemap-пути
- `src/engine/crawl/net.py`: SSL-контекст через certifi (macOS-совместимость) + единый User-Agent; `requirements.txt` (pytest/pyyaml/certifi)
- Хранилище документаций сервисов: `knowledge/services/` (INDEX.md, _TEMPLATE.md, github.md) + модуль `src/engine/knowledge/` — индексация в БД (service_docs + FTS5) и поиск
- БД: миграции 2 (crawled_pages, service_docs, FTS5) и 3 (FTS с tags)
- CLI: `crawl <url> [--robots] [--max]`, `service index|list|search`
- config.yaml: секции `crawl` (ref_sites для синтеза) и `knowledge` (auto_index_on_run)
- TODO/ROADMAP: PWA (manifest + Service Worker + offline) + Web Push (VAPID) — пуши о новых идеях/контенте (Фаза 2); канал web_push в config
- Тесты: 30 (robots, sitemap, service_docs)

## 2026-08-13 — Фаза 0: движок-скелет (продолжение)

- `plan.md` и `tasks.md` переписаны по Spec Kit (what → how → roadmap)
- `config.yaml` — полный конфиг движка (модели, источники, каналы, уровни A/B/C, валидация, расписание)
- Реализован `src/engine/store/db.py`: SQLite + 17 таблиц + миграции
- Реализован `src/engine/config.py`: config.yaml + .env, секреты только через `secret()`
- CLI: `python src/cli.py status|run` работают (лог прогона в БД), остальные — заглушки Фазы 1+
- Модули `domains`, `courses` добавлены в скелет
- Тесты: 14 (13 pass + 1 skip до git-init); фикс тестов .env.example и secrets
- Dashboard-заглушка с данными; research-артефакт перемещён в `research/`
- Создан `ingest/inbox.md` — точка ручного ввода