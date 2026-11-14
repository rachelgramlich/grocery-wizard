"""Recipe name ↔ export link helpers for meal plans (no Streamlit)."""

from __future__ import annotations

from src.grocery_wizard.integrations.notion import Recipe, recipe_export_link, recipe_lookup_key


def meal_entries_with_links(
    meal_names: list[str],
    recipes: list[Recipe],
) -> list[tuple[str, str | None]]:
    recipes_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in recipes}
    entries: list[tuple[str, str | None]] = []
    for name in meal_names:
        recipe = recipes_by_name.get(recipe_lookup_key(name))
        link = recipe_export_link(recipe) if recipe else None
        entries.append((name, link))
    return entries
