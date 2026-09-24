# Tasks — разбивка на задачи (Spec Kit)

Статусы: `[ ]` не начато, `[~]` в работе, `[x]` готово. Задачи Фазы 0 (текущая) и ближайшего продолжения.

## Фаза 0 — бутстрап

- [x] 0.1 Структура репозитория, .gitignore, .env.example, лицензии
- [x] 0.2 Документ-комплект (README/AGENTS/CHANGELOG/TODO/ROADMAP)
- [x] 0.3 Spec-артефакты (constitution/spec/plan/tasks)
- [x] 0.4 docs/ (12 документов)
- [x] 0.5 Скелет движка src/engine/* + src/cli.py
- [x] 0.6 SQLite + миграции + схема
- [x] 0.7 Тесты pytest
- [x] 0.8 Dashboard-заглушка
- [ ] 0.10 Git-репо на GitHub (public) + push
- [ ] 0.11 Вендоринг frameworks (submodules spec-kit, BMAD-METHOD)
- [ ] 0.12 GITHUB_TOKEN → живой fetch-тест GitHub trending

## Фаза 1 — движок (обкатка)

- [ ] 1.1 fetch/gh.py — GitHub trending + API (дедуп, fingerprint)
- [ ] 1.2 fetch/hn.py — Hacker News (Show/Ask)
- [ ] 1.3 fetch/rss.py + fetch/ph.py + fetch/npm.py — расширители
- [ ] 1.4 news/ — новостной пайплайн
- [ ] 1.5 ingest/ — inbox.md + add-idea CLI + email/OCR (заглушка в Фазе 1)
- [ ] 1.6 synthesize/ — кластеры, дедуп, идеи, Viability Score
- [ ] 1.7 spec/ — генератор спеков + launch-команды
- [ ] 1.8 store/ — MD-зеркала + полная запись в БД
- [ ] 1.9 index/ — многоуровневые индексы + перелинковка + wiki
- [ ] 1.10 validate/ — 5 агентов + seo/geo + links + legal (базовая версия)
- [ ] 1.11 providers/ — LLM-абстракция + кэш
- [ ] 1.12 notify/ — owner-бот базовый (статус дня)
- [ ] 1.13 KPI-отчёт weekly

## Фаза 2 — публикации (после обкатки)

- [ ] 2.1 publish/ledger.py + адаптеры (wp/tg/github-pages/cf-pages/linkedin/bluesky/vk)
- [ ] 2.2 bots/ — owner-бот (статусы, напоминания, ingest)
- [ ] 2.3 media/ — карточки/карусели/OG (HTML→PNG)
- [ ] 2.4 email/ — IMAP-ингест + OCR
- [ ] 2.5 сайт: Astro-сборка из publish/ + деплой GH Pages + CF Pages
- [ ] 2.5.1 сайт: PWA (manifest + Service Worker + offline) + Web Push (VAPID) — пуши о новых идеях/контенте
- [ ] 2.6 courses/ — первый курс
- [ ] 2.7 dashboard — полный функционал
