# CHANGELOG

Формат: дата — что изменилось — кем (bot/agent/user). Правило: **каждый** коммит, меняющий поведение или контент, добавляет запись здесь.

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

## 2026-09-24 — Фаза 0: финализация бутстрапа

- Добавлен submodule `frameworks/spec-kit` (github/spec-kit)
- Добавлен submodule `frameworks/bmad-method` (bmad-code-org/BMAD-METHOD) в .gitmodules
- Все 33 теста pytest проходят (структура, БД, конфиг, секреты, robots.txt, sitemap, service_docs, fetch fingerprint/dedup)
- Модуль fetch: GitHub Search API (topics: vibe-coding, ai-agents, llm, mcp, ai-tools) + Hacker News topstories, fingerprint-дедуп, запись в items + mentions
- Обновлён AGENTS.md с текущим статусом, командами и ключевыми деталями реализации
- Обновлён TODO.md с отметками прогресса
- Готов к `git init` + `gh repo create` + push