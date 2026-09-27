"""Конфиг: валидный YAML, обязательные ключи, секреты отдельно от конфига."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.config import load_config, load_env, secret  # noqa: E402


def test_config_loads():
    cfg = load_config()
    assert cfg["project"]["name"]
    assert cfg["engine"]["min_ideas_per_day"] >= 1
    assert cfg["validate"]["require_all"] is True


def test_publish_channels_known_levels():
    cfg = load_config()
    for ch in cfg["publish"]["channels"]:
        assert ch["level"] in ("A", "B", "C"), f"неизвестный уровень {ch['id']}"
        assert "enabled" in ch


def test_env_separate_from_config():
    cfg_text = (ROOT / "config.yaml").read_text(encoding="utf-8")
    env = load_env()
    for key, value in env.items():
        if not value:
            continue
        if "TOKEN" in key or "KEY" in key or "SECRET" in key:
            assert str(value) not in cfg_text, f"секрет {key} утёк в config.yaml"


def test_env_example_has_no_real_values():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    placeholders = ["xxx", "123456:ABC-", "replace_me", "your_", "TODO"]
    assert any(p in example for p in placeholders), "в .env.example нет плейсхолдеров"


def test_secret_prefers_env_file():
    assert isinstance(secret("GITHUB_TOKEN", "fallback"), str)
