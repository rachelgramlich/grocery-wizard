"""Shared grocery-list helpers for Streamlit sections."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.shopping.grocery_list import _normalized_item_key, merge_grocery_items
from src.grocery_wizard.shopping.line_items import parse_line_items


def meal_entries_with_links(
    meal_names: list[str],
    recipes: list[Recipe],
) -> list[tuple[str, str | None]]:
    recipes_by_name = {recipe.name.lower(): recipe for recipe in recipes}
    entries: list[tuple[str, str | None]] = []
    for name in meal_names:
        recipe = recipes_by_name.get(name.lower())
        link = recipe.link if recipe else None
        entries.append((name, link))
    return entries


def render_copy_download(
    text: str,
    *,
    label: str = "Copy list",
    key: str,
    file_name: str,
) -> None:
    """Download plain text instead of an iframe clipboard widget (lighter DOM)."""
    st.download_button(
        label=label,
        data=text.encode("utf-8"),
        file_name=file_name,
        mime="text/plain",
        key=key,
        use_container_width=True,
    )
    st.caption("Select-all in the text area above, or use Download for the same text.")


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
