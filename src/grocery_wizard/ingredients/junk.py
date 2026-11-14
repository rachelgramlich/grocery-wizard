"""Junk-line detection shared by Notion storage and grocery pipelines."""

from __future__ import annotations

from src.grocery_wizard.ingredients._cleaning import _is_junk_only
from src.grocery_wizard.ingredients.line_strips import _strip_optional_prefix


def is_junk_ingredient(line: str) -> bool:
    """Return True when a line is only prep instructions, not a grocery item."""
    return _is_junk_only(_strip_optional_prefix(line.strip()))
