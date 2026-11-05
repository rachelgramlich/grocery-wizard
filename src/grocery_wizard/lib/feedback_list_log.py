"""Attach the latest grocery list debug log to in-app feedback text."""

from __future__ import annotations

from typing import Any

from src.grocery_wizard.shopping.list_log import dump_list_log

DEBUG_LOG_JSON_HEADER = "**Latest grocery list debug log (JSON):**"
DEBUG_LOG_NOTION_HEADER = "**Latest grocery list debug log (Notion):**"
_JSON_FENCE_OPEN = "```json\n"
_JSON_FENCE_CLOSE = "\n```"


def enrich_feedback_with_list_debug_log(
    note: str,
    *,
    debug_log: dict[str, Any] | None,
    notion_url: str | None,
) -> str:
    """Append Notion link and/or JSON log from the current grocery build."""
    base = note.rstrip()
    if debug_log is None and not notion_url:
        return base

    parts: list[str] = [base] if base else []
    if url := (notion_url or "").strip():
        parts.append(f"{DEBUG_LOG_NOTION_HEADER} {url}")
    if debug_log is not None:
        json_text = dump_list_log(debug_log).strip()
        parts.append(f"{DEBUG_LOG_JSON_HEADER}\n\n{_JSON_FENCE_OPEN}{json_text}{_JSON_FENCE_CLOSE}")

    return "\n\n".join(parts)
