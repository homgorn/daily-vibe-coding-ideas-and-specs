---
name: github
kind: api
docs_url: https://docs.github.com/en/rest
api_base: https://api.github.com
auth: token
limits: "60 req/h без токена; 5000 req/h с токеном (REST); 30 req/min search"
endpoints: "GET /search/repositories; GET /repos/{owner}/{repo}; GET /repos/{owner}/{repo}/readme; GET /repositories; GET /trending"
tags: github, repos, stars, trending, open-source
status: active
---

# GitHub

## Суть
Главный источник: топ-репозитории, trending, поиск по темам (vibe-coding, ai-agents,
llm, mcp), README-файлы для анализа фич.

## Аутентификация
- `GITHUB_TOKEN` в `.env` (scopes: `repo`, `workflow` для движка; для чтения API достаточно `public_repo`/без scope)
- Создать: GitHub → Settings → Developer settings → Personal access tokens (fine-grained, read-only на public)
- Заголовок: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`

## Ограничения
- Без токена 60 req/h (не хватает на ежедневный прогон) — токен обязателен
- Search API: 30 req/min — кэшировать и дедуплицировать
- Trending (html-страница) официального API не имеет — парсинг HTML `/trending` (top 25, за день/неделю/месяц) или обход через Search API по датам
- `GET /repositories` — random list, стабильный источник «свежих»
- README: `GET /repos/{owner}/{repo}/readme` (base64) или сырой raw.githubusercontent.com

## Эндпоинты
- `GET /search/repositories?q=stars:>100 created:>YYYY-MM-DD&sort=stars` — свежие топы
- `GET /search/repositories?q=topic:vibe-coding` — по темам
- `GET /repos/{owner}/{repo}` — метаданные (stars, language, topics, description)
- `GET /users/{user}/repos` — репозитории авторов
- HTML `/trending?since=daily` — топ-25 дня (без API-лимита, но это HTML-парсинг)

## Проверено
- [x] auth работает
- [x] лимиты: search 30/min подтверждён
- [ ] парсинг /trending (HTML) — тест при реализации
