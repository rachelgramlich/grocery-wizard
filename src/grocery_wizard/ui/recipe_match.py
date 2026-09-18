"""Match weekly-plan meal names to Notion recipes and surface fix steps in the UI."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import Recipe, recipe_lookup_key


def recipe_for_plan_name(name: str, recipes: list[Recipe]) -> Recipe | None:
    """Return the Notion recipe for a planned meal name, or None if no match."""
    key = recipe_lookup_key(name)
    for recipe in recipes:
        if recipe_lookup_key(recipe.name) == key:
            return recipe
    return None


def unmatched_plan_recipe_names(selected: list[str], recipes: list[Recipe]) -> list[str]:
    keys = {recipe_lookup_key(recipe.name) for recipe in recipes}
    return [name for name in selected if name.strip() and recipe_lookup_key(name) not in keys]


def render_unmatched_plan_recipes_help(
    unmatched: list[str],
    *,
    context: str = "grocery",
) -> None:
    """Warn when plan meal titles do not match any Notion recipe name."""
    if not unmatched:
        return
    meals = ", ".join(f"**{name}**" for name in unmatched)
    st.error(f"No Notion recipe found for: {meals}")
    if context == "meals":
        st.markdown(
            "These meals are on your plan, but the app cannot load ingredients from Notion "
            "until the title matches a recipe row exactly (after trimming spaces)."
        )
    else:
        st.markdown(
            "Ingredient review will be **blank** for these meals until Notion matches your plan."
        )
    with st.expander("How to fix", expanded=True):
        st.markdown(
            "1. Open the recipe in your **Recipes** database in Notion.\n"
            "2. Edit **Name** so it matches the meal title on your plan — remove any "
            "leading or trailing spaces (or odd characters).\n"
            "3. In this app, click **Refresh from Notion** (top of the page).\n"
            "4. Return here — ingredients should populate in per-recipe review.\n"
            "\n"
            "If you renamed the recipe in Notion, update the meal on your plan to the new "
            "title (swap the meal slot or rebuild the plan)."
        )
