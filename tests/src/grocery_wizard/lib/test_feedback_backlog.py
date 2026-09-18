"""Tests for local feedback backlog storage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.grocery_wizard.lib.feedback_backlog import (
    append_feedback,
    read_feedback_backlog,
)


def test_append_feedback_writes_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.jsonl"
    append_feedback("First note", path=path, surface="Weekly recipe generation")
    append_feedback("Second note", path=path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["text"] == "First note"
    assert first["surface"] == "Weekly recipe generation"
    assert first["timestamp"]

    second = json.loads(lines[1])
    assert second["text"] == "Second note"
    assert "surface" not in second


def test_append_feedback_rejects_blank_text(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.jsonl"
    with pytest.raises(ValueError, match="non-empty"):
        append_feedback("   ", path=path)


def test_read_feedback_backlog_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"
    assert read_feedback_backlog(path) == []


def test_read_feedback_backlog_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "feedback_backlog.jsonl"
    append_feedback("Alpha", path=path)
    append_feedback("Beta", path=path, surface="Add recipe")
    entries = read_feedback_backlog(path)
    assert [entry["text"] for entry in entries] == ["Alpha", "Beta"]
    assert entries[1]["surface"] == "Add recipe"
