"""Проверка утечек секретов в git-индексируемых файлах.

Запускать перед коммитом: python -m pytest tests/test_secrets.py -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SKIP = {
    "tests", ".git", "db", "logs", "data",
    "frameworks", "wiki", "index", "publish", "assets",
}
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{36}"),            # GitHub PAT
    re.compile(r"sk-[A-Za-z0-9]{20,}"),            # OpenAI
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),          # Google
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),   # Slack
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?[A-Za-z0-9]{8,}"),
]


def git_indexed_files() -> list[Path]:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    )
    if out.returncode != 0:
        return []
    return [ROOT / f for f in out.stdout.splitlines() if f]


def test_no_secrets_in_git_files():
    files = git_indexed_files()
    if not files:
        pytest.skip("git-репо ещё не инициализирован (задача 0.10)")

    leaked: list[str] = []

    def scan(path: Path) -> None:
        rel = str(path.relative_to(ROOT))
        if any(rel.startswith(s) for s in SKIP):
            return
        if path.suffix in {".pyc"}:
            return
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return
        for pat in SECRET_PATTERNS:
            m = pat.search(content)
            if m and ".env.example" not in rel:
                leaked.append(f"{rel}: {pat.pattern}")

    for f in files:
        if f.is_file():
            scan(f)

    assert not leaked, f"Найдены секреты в git-файлах: {leaked}"