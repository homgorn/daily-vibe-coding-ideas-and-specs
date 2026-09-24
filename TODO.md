# TODO

Текущие задачи. Сверять с ROADMAP.md (фазы) — здесь операционные пункты, там — стратегические.

## Фаза 0 — бутстрап (в работе)

- [x] Структура репозитория, .gitignore, .env.example, лицензии
- [x] Документ-комплект (README/AGENTS/CHANGELOG/TODO/ROADMAP)
- [x] Spec-артефакты (constitution/spec/plan/tasks)
- [x] docs/ (12 документов)
- [x] Скелет движка src/engine/* + src/cli.py
- [x] SQLite + миграции + схема
- [x] Тесты pytest
- [x] Dashboard-заглушка
- [x] Первый research-артефакт (Spec Kit/BMAD/конкуренты/рынок)
- [x] Модуль crawl + knowledge (карточки сервисов) + PWA в планах
- [ ] Git-репо на GitHub (public) + push
- [ ] Вендоринг фреймворков: git submodule spec-kit + BMAD-METHOD
- [ ] Подключить GITHUB_TOKEN → первый живой fetch-тест (GitHub trending)
- [ ] Обкатка: 2 дня ручных прогонов (команда `python src/cli.py run`)

## Фаза 1 — обкатка пайплайна (14 дней seeding)

- [ ] Реализация fetch: GitHub trending + HN + RSS + npm (дедуп, fingerprint)
- [ ] Реализация synthesize: кластеры → идеи → Viability Score
- [ ] Реализация spec: генератор спеков (конституция + BMAD-роли + launch-команды)
- [ ] Реализация store: MD-зеркала + SQLite (все таблицы)
- [ ] Реализация index: многоуровневый индекс + перелинковка + теги
- [ ] Валидация: 5 агентов (data/text/image/video/post) + SEO/GEO-чекер + link-checker
- [ ] LLM-кэш (hash промпта → ответ), экономия токенов
- [ ] Батч-режим + инкрементальный режим (события)
- [ ] KPI-таблица и первый weekly-отчёт

## Фаза 2 — публикации и боты

- [ ] Модуль bots: owner-бот TG (статусы, напоминания, ingest) — токен от пользователя уже будет
- [ ] Модуль publish: Publish Ledger, WordPress (REST), GitHub Pages, Cloudflare Pages (поддомен)
- [ ] Модуль email: IMAP-ингест рассылок + OCR скринов
- [ ] Модуль media: карточки HTML→PNG, карусели, OG, обложки (без AI-генератора — алгоритмика)
- [ ] Модуль notify: owner-бот отчёты + напоминания
- [ ] PWA на сайте: manifest + Service Worker + offline-кэш
- [ ] Web Push (VAPID): подписки читателей, пуш «новая идея/контент/публикация» + личный канал в дашборде
- [ ] Providers: абстракция LLM-провайдеров (OpenRouter/OpenAI/Anthropic/локальные)
- [ ] Курс «Vibe Coding 101» (первый боевой, из данных недели)
- [ ] Дашборд: полноценный (лента, pipeline, publishing, рейтинги, форма идеи)
- [ ] 10: решения по авторам (персоны/бренд), About/Methodology страницы

## Фаза 3 — видео и соцсети

- [ ] Видео-модуль: YouTube + TikTok (авто-подготовка, полу-авто публикация)
- [ ] Формат-матрица видео (9:16/16:9/1:1)
- [ ] Остальные видео-площадки (IG/FB и др.) — в роадмап
- [ ] X (ручной режим + пакеты), Reddit, Quora (пакеты + напоминания)
- [ ] Мультиязычность видео (TTS, субтитры)

## Фаза 4 — реклама и масштабирование

- [ ] Meta Ads MCP пайплайн (адаптер из соседнего проекта) — креативы на каждую идею
- [ ] Авто-постинг картинок/каруселей
- [ ] Affiliate-мост, оферта Launch Kits (Lite/Standard/Premium)

## Фаза 5 — долгосрочное

- [ ] IPFS/Arweave публикация бандлов (перманет)
- [ ] Зеркала на уникальных доменах (Cloudflare API), canonical-стратегия
- [ ] API-доступ к спекам (B2B), marketplace
- [ ] Community-канал, челленджи, Mentor-агент