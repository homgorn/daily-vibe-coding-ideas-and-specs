"""Модуль knowledge: структурированное хранилище документаций сервисов.

Путь: knowledge/services/<name>.md (карточки с frontmatter).
Индексация: карточки → таблица service_docs + FTS5 (service_docs_fts).

Что это даёт: документации по фетчингу разных сервисов (API, парсинг, лимиты)
живут структурированно, ищутся через БД и используются для идей и курсов.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.store.db import init_db  # noqa: E402

SERVICES_DIR = Path(__file__).resolve().parents[3] / "knowledge" / "services"

FIELDS = {
    "name": "name",
    "kind": "kind",
    "docs_url": "docs_url",
    "api_base": "api_base",
    "auth": "auth",
    "limits": "limits",
    "endpoints": "endpoints",
    "notes": "notes",
    "tags": "tags",
    "status": "status",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Возвращает (frontmatter-поля, остальной текст). YAML-подмножество: key: value."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    _, _, after_open = text.partition("---")
    fm, sep, body = after_open.partition("---")
    if not sep:
        return {}, text
    for line in fm.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta, body


def index_service_docs(conn=None) -> list[str]:
    """Индексирует все карточки knowledge/services/*.md в service_docs + FTS.

    Возвращает список имён заиндексированных карточек.
    """
    if conn is None:
        conn = init_db()
    indexed: list[str] = []

    for md in sorted(SERVICES_DIR.glob("*.md")):
        if md.name.startswith("_") or md.name.upper() == "INDEX.MD":
            continue
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
        if not meta.get("name"):
            raise ValueError(f"карточка {md.name}: отсутствует frontmatter-поле name")

        params = {f: meta.get(f, "") for f in FIELDS}
        params["docs_path"] = f"knowledge/services/{md.name}"
        if not params["endpoints"]:
            params["endpoints"] = ""

        conn.execute(
            """INSERT INTO service_docs
               (name, kind, docs_path, docs_url, api_base, auth, limits,
                endpoints, notes, tags, status)
               VALUES (:name, :kind, :docs_path, :docs_url, :api_base, :auth,
                       :limits, :endpoints, :notes, :tags, :status)
               ON CONFLICT(name) DO UPDATE SET
                 kind=excluded.kind, docs_path=excluded.docs_path,
                 docs_url=excluded.docs_url, api_base=excluded.api_base,
                 auth=excluded.auth, limits=excluded.limits,
                 endpoints=excluded.endpoints, notes=excluded.notes,
                 tags=excluded.tags, status=excluded.status,
                 indexed_at=datetime('now')""",
            params,
        )
        row = conn.execute("SELECT id FROM service_docs WHERE name = ?", (params["name"],)).fetchone()
        _reindex_fts(conn, row["id"], params)
        indexed.append(params["name"])

    conn.commit()
    return indexed


def _reindex_fts(conn, doc_id: int, params: dict) -> None:
    conn.execute("DELETE FROM service_docs_fts WHERE rowid = ?", (doc_id,))
    conn.execute(
        "INSERT INTO service_docs_fts (rowid, name, kind, endpoints, notes, tags, docs_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_id, params["name"], params["kind"], params["endpoints"],
         params["notes"], params["tags"], params["docs_path"]),
    )


def search_services(query: str, conn=None, limit: int = 10) -> list[dict]:
    """Полнотекстовый поиск по заиндексированным карточкам сервисов."""
    if conn is None:
        conn = init_db()
    try:
        rows = conn.execute(
            "SELECT sd.name, sd.kind, sd.docs_path, sd.docs_url, sd.auth, sd.limits "
            "FROM service_docs_fts f JOIN service_docs sd ON sd.id = f.rowid "
            "WHERE service_docs_fts MATCH ? LIMIT ?",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:  # noqa: BLE001 — синтаксис запроса FTS бывает строгим
        return []


def list_services(conn=None) -> list[dict]:
    if conn is None:
        conn = init_db()
    return [dict(r) for r in conn.execute(
        "SELECT name, kind, docs_path, status FROM service_docs ORDER BY name"
    ).fetchall()]