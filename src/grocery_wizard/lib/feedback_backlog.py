"""Append-only local feedback backlog (JSON Lines) for UI capture and agent triage."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from src.grocery_wizard.config import FEEDBACK_BACKLOG_PATH

__all__ = [
    "FeedbackEntry",
    "append_feedback",
    "read_feedback_backlog",
]


class FeedbackEntry(TypedDict, total=False):
    """One line in ``feedback_backlog.jsonl``."""

    timestamp: str
    text: str
    surface: str


def append_feedback(
    text: str,
    *,
    path: Path = FEEDBACK_BACKLOG_PATH,
    surface: str | None = None,
) -> Path:
    """Append a single feedback note to the local backlog file."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("feedback text must be non-empty after stripping")

    entry: FeedbackEntry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "text": cleaned,
    }
    if surface:
        entry["surface"] = surface

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def read_feedback_backlog(path: Path = FEEDBACK_BACKLOG_PATH) -> list[FeedbackEntry]:
    """Read all feedback entries from disk (missing file → empty list)."""
    if not path.is_file():
        return []

    entries: list[FeedbackEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            entries.append(json.loads(stripped))
    return entries
