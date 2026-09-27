"""Общие фикстуры: временная БД, загрузка конфига, запрет сети в тестах.

Тесты обязаны быть офлайн: реальный LLM/API в тестах делает их медленными,
платными и нестабильными. Если тесту нужен LLM — он подставляет mock-провайдер
явно (см. tests/test_pipeline.py).
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_REAL_SOCKET_CONNECT = socket.socket.connect
_ALLOWED_HOSTS = ("127.0.0.1", "::1", "localhost")


class NetworkAccessInTests(RuntimeError):
    """Тест попытался обратиться в сеть."""


@pytest.fixture(autouse=True, scope="session")
def _block_network():
    def guarded(self, address):
        if isinstance(address, tuple) and address:
            host = str(address[0])
            if host not in _ALLOWED_HOSTS:
                raise NetworkAccessInTests(
                    f"тест обратился в сеть: {host}. "
                    "Подставь mock-провайдер или отключи autouse."
                )
        return _REAL_SOCKET_CONNECT(self, address)

    socket.socket.connect = guarded
    try:
        yield
    finally:
        socket.socket.connect = _REAL_SOCKET_CONNECT
