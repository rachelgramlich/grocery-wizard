"""Append-only local feedback backlog (Markdown inbox) for UI capture and agent triage."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from src.grocery_wizard.config import FEEDBACK_BACKLOG_PATH

__all__ = [
    "FeedbackEntry",
    "append_feedback",
    "read_feedback_backlog",
]

_METADATA_LINE = re.compile(r"^\*\*(Submitted|Surface|Context):\*\*.*\n?", re.MULTILINE)


class FeedbackEntry(TypedDict, total=False):
    """One block in ``feedback_backlog.md``."""

    timestamp: str
    text: str
    surface: str


def _format_entry_block(entry: FeedbackEntry) -> str:
    lines = ["---", "", f"**Submitted:** {entry['timestamp']}"]
    if surface := entry.get("surface"):
        lines.append(f"**Surface:** {surface}")
    lines.extend(["", entry["text"].rstrip(), ""])
    return "\n".join(lines)


def append_feedback(
    text: str,
    *,
    path: Path = FEEDBACK_BACKLOG_PATH,
    surface: str | None = None,
) -> Path:
    """Append a single feedback note to the local markdown inbox."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("feedback text must be non-empty after stripping")

    entry: FeedbackEntry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "text": cleaned,
    }
    if surface:
        entry["surface"] = surface

    block = _format_entry_block(entry)
    path.parent.mkdir(parents=True, exist_ok=True)

    prefix = ""
    if path.is_file() and path.read_text(encoding="utf-8").strip():
        prefix = "\n\n"

    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + block)
    return path


def read_feedback_backlog(path: Path = FEEDBACK_BACKLOG_PATH) -> list[FeedbackEntry]:
    """Read all feedback entries from disk (missing file → empty list)."""
    if not path.is_file():
        return []

    raw = path.read_text(encoding="utf-8")
    entries: list[FeedbackEntry] = []
    for raw_chunk in re.split(r"\n---\n", raw):
        block = raw_chunk.strip()
        if not block:
            continue
        if block.startswith("---"):
            block = block.removeprefix("---").strip()

        submitted = re.search(r"\*\*Submitted:\*\*\s*(.+)", block)
        timestamp = submitted.group(1).strip() if submitted else ""
        surface_match = re.search(r"\*\*Surface:\*\*\s*(.+)", block)
        surface = surface_match.group(1).strip() if surface_match else None
        body = _METADATA_LINE.sub("", block).strip()

        entry: FeedbackEntry = {"timestamp": timestamp, "text": body}
        if surface:
            entry["surface"] = surface
        entries.append(entry)
    return entries
