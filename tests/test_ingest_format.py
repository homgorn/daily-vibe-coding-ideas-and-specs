"""Ingest: the documented inbox format must parse, placeholders must not."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine.ingest as ingest_mod  # noqa: E402
from engine.ingest import parse_inbox  # noqa: E402

SHIPPED_INBOX = """# Inbox — ручной ввод материалов

Сюда клади ссылки / идеи / файлы. Обрабатывается ингест-пайплайном (Фаза 1).

Формат: одна запись = строка `- [ ] ссылка | короткое описание`

## Ссылки и идеи

- [ ] (пусто — добавь первую запись, например: https://github.com/foo/bar | идея для проекта)

## Правила

- Скриншоты и PDF — в `candidates/`
- Файлы-черновики — в `manual/`
- Обработанные записи автоматически помечаются `[x]` и переносятся вниз в Заархивировано
"""


def write_inbox(tmp_path, monkeypatch, text: str):
    path = tmp_path / "inbox.md"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(ingest_mod, "INBOX_PATH", path)
    return path


def test_shipped_inbox_yields_no_ideas(tmp_path, monkeypatch):
    """The inbox template must not manufacture ideas out of its own instructions."""
    write_inbox(tmp_path, monkeypatch, SHIPPED_INBOX)
    items = parse_inbox()
    assert items == [], [i.title for i in items]


def test_documented_line_format_parses(tmp_path, monkeypatch):
    write_inbox(
        tmp_path,
        monkeypatch,
        "# Inbox\n\n## Ссылки и идеи\n\n"
        "- [ ] https://github.com/vercel/next.js | App framework with AI router\n"
        "- [ ] https://github.com/langchain-ai/langchain | Agent framework, huge docs\n",
    )
    items = parse_inbox()
    assert len(items) == 2, [i.title for i in items]
    titles = " ".join(i.title for i in items).lower()
    assert "next.js" in titles
    assert "langchain" in titles
    descriptions = " ".join(i.description for i in items).lower()
    assert "app framework" in descriptions
    assert "agent framework" in descriptions


def test_real_idea_survives_next_to_placeholder(tmp_path, monkeypatch):
    write_inbox(
        tmp_path,
        monkeypatch,
        "# Inbox\n\n## Ссылки и идеи\n\n"
        "- [ ] (пусто — добавь первую запись, например: https://example.com/x | пример)\n"
        "- [ ] https://github.com/real/thing | настоящая идея\n",
    )
    items = parse_inbox()
    assert len(items) == 1
    assert "example.com" not in (items[0].url or "")
    assert "real" in (items[0].url or "")


def test_key_value_format_still_supported(tmp_path, monkeypatch):
    write_inbox(
        tmp_path,
        monkeypatch,
        "# Inbox\n\n## My Idea Title\nURL: https://example.com/a\n"
        "Description: does a thing\ntags: ai, tools\n",
    )
    items = parse_inbox()
    assert len(items) == 1
    assert items[0].title == "My Idea Title"
    assert items[0].url == "https://example.com/a"
    assert items[0].description == "does a thing"
    assert items[0].tags == ["ai", "tools"]


@pytest.mark.parametrize(
    "line",
    [
        "- Скриншоты и PDF — в `candidates/`",
        "- Файлы-черновики — в `manual/`",
        "- Обработанные записи помечаются `[x]`",
        "Формат: одна запись = строка",
    ],
)
def test_instruction_lines_are_never_items(tmp_path, monkeypatch, line):
    write_inbox(tmp_path, monkeypatch, f"# Inbox\n\n## Правила\n\n{line}\n")
    assert parse_inbox() == []


def test_process_inbox_reports_zero_for_template(tmp_path, monkeypatch):
    write_inbox(tmp_path, monkeypatch, SHIPPED_INBOX)
    monkeypatch.setattr(ingest_mod, "CANDIDATES_DIR", tmp_path / "nope-cand")
    monkeypatch.setattr(ingest_mod, "MANUAL_DIR", tmp_path / "nope-manual")
    stats = ingest_mod.process_inbox()
    assert stats["inbox"] == 0
    assert stats["total"] == 0
