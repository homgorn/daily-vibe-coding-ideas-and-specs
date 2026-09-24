"""Модуль ingest: ручной ввод (inbox.md, add-idea), файлы, скрины/OCR, email.

Фаза 0: интерфейс. Фаза 1: inbox + add-idea. Фаза 2: email + OCR.
"""

from __future__ import annotations


def process_inbox() -> list[str]:
    """Сканирует ingest/inbox.md и candidates/, возвращает новые записи. Фаза 1."""
    raise NotImplementedError("ingest: Фаза 1")
