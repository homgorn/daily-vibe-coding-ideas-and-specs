# Сервисы — реестр документаций по фетчингу/парсингу

Карточки: `knowledge/services/<name>.md` (frontmatter + заметки).
Индексация в БД: `python src/cli.py service index` → таблица `service_docs` + FTS5-поиск.

## Как добавить документацию сервиса

1. Скопируй `_TEMPLATE.md` → `knowledge/services/<name>.md`
2. Заполни frontmatter (обязательно `name` и `kind`) + заметки по фетчингу
3. Запусти `python src/cli.py service index`

Сюда складываются документации API/скрейпинга/RSS любых сервисов — это сырьё
для референсов идей, спеков и курсов.

## Карточки

| Сервис | Тип | Файл | Статус |
|---|---|---|---|
| GitHub | api | [github.md](github.md) | active |
