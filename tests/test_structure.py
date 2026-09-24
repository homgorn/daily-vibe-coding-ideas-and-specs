"""Структура репозитория: все обязательные директории/файлы на месте."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "src/engine", "src/engine/store", "src/engine/fetch", "src/engine/news",
    "src/engine/ingest", "src/engine/synthesize", "src/engine/spec",
    "src/engine/media", "src/engine/validate", "src/engine/publish",
    "src/engine/index", "src/engine/notify", "src/engine/courses",
    "src/engine/bots", "src/engine/providers", "src/engine/email",
    "src/engine/domains",
    "data", "docs", "docs/legal", "docs/10-decisions",
    "frameworks", "research", "ingest", "publish", "prompts", "assets",
    "candidates", "manual", "knowledge", "logs", "index", "wiki",
    "dashboard", "tests", "db",
]

REQUIRED_FILES = [
    "config.yaml", ".env.example", ".gitignore", "README.md", "AGENTS.md",
    "CHANGELOG.md", "TODO.md", "ROADMAP.md", "constitution.md",
    "spec.md", "plan.md", "tasks.md", "src/cli.py",
    "src/engine/config.py", "src/engine/store/db.py",
]


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"Отсутствуют директории: {missing}"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"Отсутствуют файлы: {missing}"


def test_ingest_inbox_exists():
    inbox = ROOT / "ingest" / "inbox.md"
    assert inbox.exists(), "ingest/inbox.md обязателен (точка ручного ввода)"


def test_no_secrets_in_gitignored_env():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "=" in env_example
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore, ".env должен быть в .gitignore"
