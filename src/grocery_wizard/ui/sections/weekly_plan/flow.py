"""Orchestrates the Create weekly plan tab."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import cached_query_recipes
from src.grocery_wizard.ui.sections.weekly_plan.grocery_wizard import render_grocery_list_section
from src.grocery_wizard.ui.sections.weekly_plan.plan_entry import (
    _render_weekly_plan_entry,
    render_meals_section,
)
from src.grocery_wizard.ui.sections.weekly_plan.state import (
    _current_plan_names,
    _invalidate_stale_grocery_result,
)


@st.fragment(key="weekly_plan_meals")
def _weekly_plan_meals_fragment(db: NotionRecipesDB, all_recipes: list[Recipe]) -> None:
    render_meals_section(db, all_recipes=all_recipes)


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

    db = get_db()
    with st.spinner("Loading recipes from Notion…"):
        all_recipes = cached_query_recipes(db)

    _weekly_plan_meals_fragment(db, all_recipes)
    _weekly_plan_grocery_fragment(db, all_recipes)
