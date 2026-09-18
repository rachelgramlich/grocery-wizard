"""Shared grocery-list helpers for Streamlit sections."""

from __future__ import annotations

import html
import json

import streamlit as st
import streamlit.components.v1 as components

from src.grocery_wizard.integrations.notion import Recipe, recipe_lookup_key
from src.grocery_wizard.shopping.grocery_list import _normalized_item_key, merge_grocery_items
from src.grocery_wizard.shopping.line_items import parse_line_items
from src.grocery_wizard.ui.theme import GW_THEME


def meal_entries_with_links(
    meal_names: list[str],
    recipes: list[Recipe],
) -> list[tuple[str, str | None]]:
    recipes_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in recipes}
    entries: list[tuple[str, str | None]] = []
    for name in meal_names:
        recipe = recipes_by_name.get(recipe_lookup_key(name))
        link = recipe.link if recipe else None
        entries.append((name, link))
    return entries


def render_copy_button(
    text: str,
    *,
    label: str = "Copy",
    key: str,
) -> None:
    """Render a full-width control that copies ``text`` to the clipboard."""
    payload = json.dumps(text)
    label_json = json.dumps(label)
    copied_json = json.dumps("Copied!")
    safe_label = html.escape(label)
    tokens = GW_THEME
    components.html(
        f"""
        <style>
          .gw-copy-btn {{
            width: 100%;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.5rem;
            background: {tokens.accent};
            color: {tokens.on_accent};
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
          }}
          .gw-copy-btn:hover {{
            filter: brightness(1.05);
          }}
        </style>
        <button id="gw-copy-{key}" type="button" class="gw-copy-btn">{safe_label}</button>
        <script>
          (function () {{
            const btn = document.getElementById("gw-copy-{key}");
            const text = {payload};
            const label = {label_json};
            const copied = {copied_json};
            btn.addEventListener("click", function () {{
              navigator.clipboard.writeText(text).then(function () {{
                btn.textContent = copied;
                setTimeout(function () {{ btn.textContent = label; }}, 2000);
              }});
            }});
          }})();
        </script>
        """,
        height=52,
    )
    st.caption("Select-all in the text area above, or use Copy for the same text.")


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
