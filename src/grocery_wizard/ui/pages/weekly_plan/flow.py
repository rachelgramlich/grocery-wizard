"""Orchestrates the Create weekly plan page."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.notion_cache import cached_query_recipes
from src.grocery_wizard.ui.pages.weekly_plan.grocery_list_ui import render_grocery_list_section
from src.grocery_wizard.ui.pages.weekly_plan.plan_entry import (
    _ensure_plan_session_defaults,
    _render_meal_count_input,
    _render_weekly_plan_entry,
    _sync_plan_length_to_meal_count,
    render_meals_section,
)
from src.grocery_wizard.ui.pages.weekly_plan.state import (
    _current_plan_names,
    _invalidate_stale_grocery_result,
)


@st.fragment(key="weekly_plan_meals")
def _weekly_plan_meals_fragment(
    db: NotionRecipesDB,
    all_recipes: list[Recipe],
    *,
    meal_count: int,
) -> None:
    render_meals_section(db, all_recipes=all_recipes, meal_count=meal_count)


@st.fragment(key="weekly_plan_grocery")
def _weekly_plan_grocery_fragment(db: NotionRecipesDB, all_recipes: list[Recipe]) -> None:
    render_grocery_list_section(
        db,
        all_recipes=all_recipes,
        current_plan=_current_plan_names(),
    )


def render_create_weekly_plan() -> None:
    st.markdown("**Steps:** 1. Meals → 2. Grocery list")

    _invalidate_stale_grocery_result()

    if not _render_weekly_plan_entry():
        return

    _ensure_plan_session_defaults()
    meal_count = _render_meal_count_input()
    _sync_plan_length_to_meal_count(meal_count)

    db = get_db()
    with loading_indicator("Loading recipes from Notion…"):
        all_recipes = cached_query_recipes(db)

    _weekly_plan_meals_fragment(db, all_recipes, meal_count=meal_count)
    _weekly_plan_grocery_fragment(db, all_recipes)
