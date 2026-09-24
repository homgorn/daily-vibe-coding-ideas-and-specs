"""Общие сетевые хелперы: SSL-контекст (certifi → системные), User-Agent."""

from __future__ import annotations

import ssl

DEFAULT_UA = "DailyVibeEngine/0.1 (+https://github.com/daily-vibe-coding-ideas-and-specs)"


def ssl_context() -> ssl.SSLContext:
    """SSL-контекст с проверкой сертификатов (macOS-совместимость)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()