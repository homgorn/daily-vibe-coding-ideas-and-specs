"""Конфигурация: config.yaml + .env.

Правило: секреты ТОЛЬКО в .env, конфиг — без секретов.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"
ENV_PATH = ROOT / ".env"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml не найден: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_env() -> dict[str, str]:
    """Загружает .env в dict (без модификации os.environ)."""
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def secret(key: str, default: str = "") -> str:
    """Достаёт секрет: .env → os.environ → default."""
    return load_env().get(key) or os.environ.get(key, default)
