"""SQLite-хранилище: соединение, миграции, инициализация схемы.

Правила:
- db/engine.db коммитится в git (бэкап); journal/wal — игнорируются
- Все изменения схемы — только через MIGRATIONS (schema_migrations)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "db" / "engine.db"

MIGRATIONS: list[tuple[int, str]] = [
    (1, """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version    INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sources (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        kind        TEXT NOT NULL,          -- github | hn | rss | npm | manual | email | news
        url         TEXT,
        enabled     INTEGER NOT NULL DEFAULT 1,
        last_run_at TEXT
    );

    CREATE TABLE IF NOT EXISTS items (
        id          INTEGER PRIMARY KEY,
        fingerprint TEXT NOT NULL UNIQUE,   -- дедуп по хэшу (title+url+source)
        source_id   INTEGER REFERENCES sources(id),
        title       TEXT NOT NULL,
        url         TEXT,
        description TEXT,
        raw         TEXT,                   -- сырые данные фетча (JSON)
        meta        TEXT,                   -- доп. метаданные (JSON)
        fetched_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS mentions (
        item_id  INTEGER NOT NULL REFERENCES items(id),
        day      TEXT NOT NULL,             -- YYYY-MM-DD
        PRIMARY KEY (item_id, day)
    );

    CREATE TABLE IF NOT EXISTS news_items (
        id           INTEGER PRIMARY KEY,
        item_id      INTEGER REFERENCES items(id),
        headline     TEXT NOT NULL,
        source_name  TEXT,
        url          TEXT,
        published_at TEXT,
        summary      TEXT,
        processed    INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS clusters (
        id         INTEGER PRIMARY KEY,
        name       TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS item_clusters (
        item_id    INTEGER NOT NULL REFERENCES items(id),
        cluster_id INTEGER NOT NULL REFERENCES clusters(id),
        PRIMARY KEY (item_id, cluster_id)
    );

    CREATE TABLE IF NOT EXISTS ideas (
        id            INTEGER PRIMARY KEY,
        item_id       INTEGER REFERENCES items(id),   -- NULL для ручных идей
        title         TEXT NOT NULL,
        summary       TEXT,
        origin        TEXT NOT NULL DEFAULT 'research', -- research | user | news | ingest
        source_url    TEXT,
        status        TEXT NOT NULL DEFAULT 'new',     -- new|watching|spec|shipped|dead
        viability     TEXT,                            -- JSON: market/competition/time_to_mvp/risk/score/confidence
        rating        INTEGER,                         -- 1..5 от владельца
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS specs (
        id         INTEGER PRIMARY KEY,
        idea_id    INTEGER NOT NULL REFERENCES ideas(id),
        path       TEXT NOT NULL,
        status     TEXT NOT NULL DEFAULT 'draft',      -- draft|validated|published|failed
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS tags (
        id   INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS item_tags (
        item_id INTEGER NOT NULL REFERENCES items(id),
        tag_id  INTEGER NOT NULL REFERENCES tags(id),
        PRIMARY KEY (item_id, tag_id)
    );

    CREATE TABLE IF NOT EXISTS related_links (
        from_id  INTEGER NOT NULL,
        to_id    INTEGER NOT NULL,
        relation TEXT NOT NULL,             -- similar | cluster | source | spec
        weight   REAL NOT NULL DEFAULT 1.0,
        PRIMARY KEY (from_id, to_id, relation)
    );

    CREATE TABLE IF NOT EXISTS content_bundles (
        id         INTEGER PRIMARY KEY,
        idea_id    INTEGER NOT NULL REFERENCES ideas(id),
        kind       TEXT NOT NULL,           -- spec|prompts|marketing|investor|ads|visuals|video|course
        path       TEXT,
        status     TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS publish_ledger (
        id             INTEGER PRIMARY KEY,
        artifact_type  TEXT NOT NULL,       -- idea|spec|bundle|list|post|video
        artifact_id    INTEGER NOT NULL,
        channel        TEXT NOT NULL,       -- github_pages|wordpress|telegram|...
        status         TEXT NOT NULL DEFAULT 'draft', -- draft|approved|queued|sent|failed
        url            TEXT,
        error          TEXT,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        published_at   TEXT
    );

    CREATE TABLE IF NOT EXISTS reminders (
        id         INTEGER PRIMARY KEY,
        text       TEXT NOT NULL,
        due_at     TEXT,
        status     TEXT NOT NULL DEFAULT 'pending',
        channel    TEXT NOT NULL DEFAULT 'telegram_owner'
    );

    CREATE TABLE IF NOT EXISTS run_logs (
        id         INTEGER PRIMARY KEY,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        finished_at TEXT,
        status     TEXT NOT NULL DEFAULT 'running',  -- running|ok|failed
        phase      TEXT,
        details    TEXT
    );

    CREATE TABLE IF NOT EXISTS llm_cache (
        key_hash   TEXT PRIMARY KEY,
        prompt     TEXT NOT NULL,
        response   TEXT NOT NULL,
        model      TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """),
    (2, """
    CREATE TABLE IF NOT EXISTS crawled_pages (
        id             INTEGER PRIMARY KEY,
        url            TEXT NOT NULL UNIQUE,
        domain         TEXT NOT NULL,
        robots_allowed INTEGER NOT NULL DEFAULT 1,
        status         INTEGER,
        content_hash   TEXT,
        content_path   TEXT,
        crawled_at     TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS service_docs (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,       -- имя сервиса (slug)
        kind        TEXT NOT NULL DEFAULT 'api',-- api|scraper|rss|site|sdk|docs
        docs_path   TEXT,                        -- knowledge/services/<name>.md
        docs_url    TEXT,                        -- официальная документация
        api_base    TEXT,
        auth        TEXT,                        -- тип: token|oauth|none|key (подробности в карточке)
        limits      TEXT,                        -- rate limits / квоты
        endpoints   TEXT,                        -- ключевые эндпоинты (через ";")
        notes       TEXT,                        -- заметки фетчинга/парсинга
        tags        TEXT,
        status      TEXT NOT NULL DEFAULT 'active',
        indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS service_docs_fts
        USING fts5(name, kind, endpoints, notes, docs_path);
    """),
    (3, """
    DROP TABLE IF EXISTS service_docs_fts;
    CREATE VIRTUAL TABLE IF NOT EXISTS service_docs_fts
        USING fts5(name, kind, endpoints, notes, tags, docs_path);
    """),
]


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Применяет неприменённые миграции по порядку."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
    for version, sql in sorted(MIGRATIONS):
        if version in applied:
            continue
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        conn.commit()


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = get_conn(db_path)
    migrate(conn)
    return conn
