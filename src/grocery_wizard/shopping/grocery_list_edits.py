"""Merge, parse, and edit grocery list lines (no Streamlit)."""

from __future__ import annotations

from src.grocery_wizard.shopping.grocery_list import _normalized_item_key, merge_grocery_items
from src.grocery_wizard.shopping.line_items import parse_line_items


def parse_line_items_text(text: str) -> list[str]:
    return parse_line_items(text)


def compute_grocery_drafts(
    items: list[str],
    readd: list[str],
    additional_text: str,
    *,
    recurring_items: list[str] | None = None,
    run_removals: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    extras = parse_line_items_text(additional_text)
    recurring = list(recurring_items or [])
    draft_items = merge_grocery_items(items, readd)
    final_items = merge_grocery_items(items, readd, recurring, extras)
    if run_removals:
        final_items = apply_run_removals(final_items, run_removals)
    return draft_items, final_items


def removal_matches_grocery_line(line: str, removal: str) -> bool:
    """True when *removal* targets this buy-list *line* (exact or same normalized item)."""
    stripped_line = line.strip()
    stripped_removal = removal.strip()
    if not stripped_line or not stripped_removal:
        return False
    if stripped_line.lower() == stripped_removal.lower():
        return True
    return _normalized_item_key(stripped_line) == _normalized_item_key(stripped_removal)


def apply_run_removals(items: list[str], removals: set[str]) -> list[str]:
    if not removals:
        return items
    removal_list = [name for name in removals if name.strip()]
    filtered: list[str] = []
    for line in items:
        if any(removal_matches_grocery_line(line, removal) for removal in removal_list):
            continue
        filtered.append(line)
    return filtered


def grocery_line_matches_name(line: str, name: str) -> bool:
    return removal_matches_grocery_line(line, name)
