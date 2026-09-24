---
name: replace-with-service-slug
kind: api                # api | scraper | rss | site | sdk | docs
docs_url:
api_base:
auth:                    # token | oauth | key | none (подробности ниже)
limits:
endpoints:               # через ";"
tags:
status: active           # active | beta | dead | no_docs
---

# <Название сервиса>

## Суть
Что за сервис, зачем фетчим (референсы идей, спеки, курсы).

## Аутентификация
Тип, как получить токен/ключ, где хранить (только .env).

## Ограничения
Rate limits, квоты, требования к User-Agent, запреты (robots.txt / ToS).

## Эндпоинты / как парсить
- GET /endpoint — что даёт, параметры
- RSS/sitemap: URL, формат
- Скрейпинг: что парсим, селекторы, анти-бот меры

## Проверено
- [ ] auth работает
- [ ] лимиты не выбиты
- [ ] парсинг корректный
