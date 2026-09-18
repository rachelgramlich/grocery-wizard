"""Tests for local feedback backlog storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.grocery_wizard.lib.feedback_backlog import (
    append_feedback,
    read_feedback_backlog,
)


def test_append_feedback_writes_markdown_blocks(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.md"
    append_feedback("First note", path=path, surface="Weekly recipe generation")
    append_feedback("Second note", path=path)

    text = path.read_text(encoding="utf-8")
    assert "**Submitted:**" in text
    assert "**Surface:** Weekly recipe generation" in text
    assert "First note" in text
    assert "Second note" in text
    assert text.count("\n---\n") >= 1


def test_append_feedback_rejects_blank_text(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.md"
    with pytest.raises(ValueError, match="non-empty"):
        append_feedback("   ", path=path)


def test_read_feedback_backlog_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.md"
    assert read_feedback_backlog(path) == []


def test_read_feedback_backlog_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.md"
    append_feedback("Alpha", path=path)
    append_feedback("Beta", path=path, surface="Add recipe")
    entries = read_feedback_backlog(path)
    assert [entry["text"] for entry in entries] == ["Alpha", "Beta"]
    assert entries[1]["surface"] == "Add recipe"
    assert entries[0]["timestamp"]
    assert entries[1]["timestamp"]
