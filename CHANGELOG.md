# CHANGELOG

Формат: дата — что изменилось — кем (bot/agent/user). Правило: **каждый** коммит, меняющий поведение или контент, добавляет запись здесь.

## 2026-09-27 — Живой LLM: OpenRouter free-tier, фолбэки, бюджеты, офлайн-тесты

### Найдено при подключении живого LLM: спеки были пустыми
- `generate_spec()` звал LLM, но `json.loads` падал на fenced-JSON от моделей и код **молча** уходил в `_fallback_spec()` — шаблон с `See summary above.`, `Core feature (P0)`, `Python + SQLite + Markdown` и фиктивными `Cited Sources`
- **Все 12 спек в репо были шаблонами.** Валидация давала 12/12 PASS: заглушка внешне неотличима от настоящей спеки, агент `data` видел заголовок `Cited Sources` и считал цитирование выполненным. Публиковалась пустота, проходящая все гейты — прямое нарушение конституции §1 и §3
- `extract_json_object()`: снимает ```json / ``` ограждения и прозу вокруг, затем скобочным сканом (с учётом строк и экранирований) ищет внешний `{...}`
- Провал парсинга → тело заменяется на `FALLBACK_MARKER` и явное предупреждение. Больше **не** пишутся `TBD`, выдуманные секции и фиктивные `Cited Sources`
- **9-й агент валидации — `generation`**: находит `FALLBACK_MARKER` и проваливает артефакт. Пустое не публикуется
- Отсутствующее поле рендерится как `(not provided by model)`, а не `TBD` — видно, чего нет
- Решение зафиксировано: `docs/10-decisions/ADR-006-fail-loud-spec-generation.md`
- Тесты: `tests/test_spec_generation.py` (7), `tests/test_validate_generation.py` (3)
- `tools/reset_fallback_specs.py` + `tools/regen_specs.py` + `tools/check_spec_json.py`

### Ингест: шаблон inbox производил идеи
- `parse_inbox()` разбивал файл по `## ` и каждую секцию считал идеей. Шаблон `ingest/inbox.md` отдавал плейсхолдер `- [ ] (пусто — добавь первую запись, например: https://github.com/foo/bar | ...)` как идею с URL `github.com/foo/bar`, а секцию `## Правила` — как ещё одну идею
- Задокументированный в самом inbox формат (`- [ ] ссылка | описание`) **не поддерживался** парсером — следовало писать `## Title` + `URL:`. Владелец читал инструкцию и писал в формате, который молча ломался
- Переписано: чекбокс-строки дают самостоятельные идеи (`title` из слага URL, описание после `|`); key/value-блок и голый URL внутри секции сохраняют заголовок секции как title (обратная совместимость)
- Пропускаются секции-инструкции (`Правила`, `Rules`, `Формат`, архив) и строки-плейсхолдеры. Детектор плейсхолдеров ключуется на прозу, а не на домены: реальная ссылка на `example.com` допустима
- Тесты: `tests/test_ingest_format.py` (9), включая «шаблон из репо не должен порождать идеи»

### Публикация не была отфильтрована валидацией
- `build_site()` рендерил **все** файлы из `publish/en/{ideas,specs}` без проверки. Артефакт, проваливший валидацию, всё равно попадал в HTML, RSS и sitemap — конституция §3 («публикуется только то, что прошло все агенты») не исполнялась
- Добавлен `_filter_validated()`: рендер = публикация, поэтому гейт стоит именно здесь, а не в вызывающем коде. Возвращает `(kept, dropped)`, в статистику попадают `excluded` и `excluded_names` с причинами
- CLI печатает `excluded unvalidated=N` — публикация стала наблюдаемой
- Фикстура `tests/test_site.py::_write_idea` была невалидна по правилам самого проекта (не хватало `origin`) и раньше просто рендерилась; доведена до валидной, гейт не ослаблен
- Тесты: `tests/test_site_validation_gate.py` (2)

### Требует решения владельца
- `constitution.md` §3 называет **5** валидационных агентов. Реализовано 9: 5 ядро (data/text/image/video/post) + seo_geo + links + legal + **generation**. Число разошлось с кодом — правилом это не является, но текст устарел
- Правка конституции требует ADR и согласия владельца, поэтому не выполнялась молча

### max_tokens: замер, а не догадка
- Вопрос «4096 — не много ли?» закрыт замерами (`tools/bench_max_tokens.py`, `tools/diagnose_truncation.py`, `tools/inspect_response.py`) на `nvidia/nemotron-3-ultra-550b-a55b:free` с реальным спека-промптом:

  | max_tokens | finish_reason | completion | распарсилось |
  |---|---|---|---|
  | 2000 | length | 2000 | нет |
  | 4000 | length | 4000 | нет |
  | 6000 | length | 6000 | нет |
  | 8000 | length | 8000 | нет |
  | 16000 | stop | 9727 | **нет** |

- **Поднимать лимит нельзя**: модели нужно >9.7k токенов на 12 секций, и даже когда она заканчивает сама (`stop`), JSON не парсится. Плюс 16k на free-пуле = минуты в очереди
- **4 секции за один вызов = 2331 токен, `finish_reason=stop`, парсится надёжно**
- Решение: `SPEC_GROUPS` — генерация разбита на 3 вызова по 4 секции (`Problem and value`, `Architecture`, `Shipping`). Меньшие группы быстрее, не обрезаются и теряют 4 секции вместо 12 при сбое
- Частичный успех возможен: упавшая группа даёт `(not provided by model)` и пометку `*Partial spec: ...*`, а не отменяет всю спеку
- Промпт усилен правилами grounding: только источники, никаких выдуманных статистик/дат/версий/URL, `cited_sources` только из source materials
- Тесты: `tests/test_spec_grouping.py` (6) — покрытие секций, размер группы, частичный сбой

### Повтор на обрезанную группу + max_tokens 3200
- После разбивки `audit_specs.py` показал 8 из 12 секций на спеку. Разбор кэша LLM (`tools/audit_cache_keys.py`, `tools/inspect_cache_tail.py`) дал точную причину: у всех длинных ответов `ends_with_brace: False` — это **обрезка**. JSON-экранирование markdown съедает токены, и группа из 4 секций обрывалась на 5500–7100 символах при `max_tokens: 2000`
- `models.max_tokens_by_stage.expensive`: 2000 → **3200**. `max_tokens` — потолок, а не цель, поэтому лимит выше естественной длины ответа не стоит ничего; 16000 стоил бы минут очереди
- Группа, которая вернулась непарсимым JSON или ответила только частью ключей, переспрашивается один раз — **только по недостающим ключам** (`MAX_GROUP_ATTEMPTS = 2`). Уже полученные секции не запрашиваются заново
- Промпт усилен прямым требованием: «exactly these keys and no others», «every key must be present», «the JSON must be complete and closed», плюс просьба держать секции краткими
- `SPEC_GROUPS` уточнён до **4 групп**: `Problem and value` (4), `Stack and data` (2), `Interfaces and UX` (2), `Shipping` (4). Замер показал, что 3200 хватает 4 секциям из 5 групп, но `Architecture` обрывалась дважды подряд — `tech_stack` и `api` заставляют модель писать большие блоки кода. Урок: средняя длина группы не показательна, показательна самая длинная секция в ней
- Тесты: `tests/test_spec_grouping.py` вырос до 11 — отдельно проверено, что послушная модель даёт ровно по одному вызову на группу без повторов, а повтор спрашивает только недостающее
- Побочно выяснено и исправлено: сетевая ошибка (`getaddrinfo failed`) прогоняла цепочку фолбэков целиком — 3 попытки × 3 модели × 3 группы чистого ожидания. `URLError` теперь прерывает цепочку сразу

### Провайдер не ретраил конфиг-ошибки
- 400 «not a valid model ID» повторялся 4 раза подряд (опечатка `nemotron-3.ultra` вместо `nemotron-3-ultra`). Повтор не исправляет неверный ID — только тратит бюджет и прячет причину
- `OpenRouterProvider` пробрасывает без ретраев 400/401/402/403/404/422; повторяются 429 и 5xx
- Тесты: `test_config_errors_are_not_retried` (400 → одна попытка), `test_rate_limit_is_retried` (429 → повторы, успех)

### Провайдеры
- `config.yaml`: добавлен ключ `models.provider` (`openrouter`) — **его не было**, реестр молча уходил в mock, и «зелёный» прогон ничего не доказывал
- Free-модели по стадиям: `nvidia/nemotron-3.5-lightning` (cheap, ~97 tok/s), `nvidia/nemotron-3-super-120b-a12b` (medium, ~60), `nvidia/nemotron-3-ultra-550b-a55b` (expensive, ~50)
- `models.fallbacks` — при `429 "temporarily rate-limited upstream"` движок перебирает запасные модели вместо падения
- `models.max_tokens_by_stage` (700/1200/2000) вместо общих 4096: большие лимиты на free-пуле = минуты стояния в очереди (замер: 4096 → ~7 мин/вызов, 700 → 7–14 с)
- `models.budget_minutes` — потолок LLM-времени на стадию; по исчерпании стадия возвращает `skipped_budget`, прогон продолжается
- `OpenRouterProvider`: ретраи с backoff, `HTTP-Referer`/`X-Title`, `list_models()` тянет реальный список, 401/402/403 пробрасываются без ретраев
- `run_spec_generation` больше не падает целиком: ошибки идут в `errors`, бюджет — в `skipped_budget`

### Тесты (79 → 87)
- **`tests/conftest.py` теперь блокирует сеть** (`socket.connect`) на всю сессию: `test_pipeline.py` назывался «offline», но мокал только fetch/news — synthesize/spec ходили в реальный LLM. На живом ключе прогон тестов висел >20 мин вместо 26 с
- `test_pipeline.py` принудительно ставит `provider: mock`
- `test_config.py::test_env_separate_from_config` сравнивал и **пустые** значения: `"" in config_text` всегда `True`, поэтому любая пустая `TOKEN=` ломала тест
- Новый `tests/test_providers.py`: роутинг по стадиям, порядок фолбэков, отказ при отказе всех моделей, потолок бюджета, попадание в кэш
- `tools/check_models.py`, `tools/bench_models.py`, `tools/probe_free_models.py` — диагностика free-моделей

### Устойчивость
- `_close_stale_runs()`: убитые прогоны больше не висят в статусе `running` вечно — следующий запуск помечает их `failed` с пометкой `stale`

### Инфраструктура
- `.env`: `OPENROUTER_API_KEY` и `CF_API_TOKEN` (проверен, активен), `LLM_PROVIDER=openrouter`
- `site.base_url` = `https://homgorn.github.io/daily-vibe-coding-ideas-and-specs` вместо плейсхолдера
- `GITHUB_TOKEN` из сообщения пользователя **невалиден** (`Bad credentials`) — нужен новый, иначе KPI «≥30 items/день» не закрывается стабильно

### Прогон #17 (живой, end-to-end)
`fetch 11 → news 5 → synthesize 3 идеи → spec 1 → validate 12/12 → index 24 → site 29 страниц, 0 битых ссылок` за **172 с**, LLM-время 2.17 мин.

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