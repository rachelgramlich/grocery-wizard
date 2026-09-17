"""Orchestrates the Create weekly plan tab."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import cached_query_recipes
from src.grocery_wizard.ui.sections.weekly_plan.grocery_wizard import render_grocery_list_section
from src.grocery_wizard.ui.sections.weekly_plan.plan_entry import (
    _render_weekly_plan_entry,
    render_meals_section,
)
from src.grocery_wizard.ui.sections.weekly_plan.state import _invalidate_stale_grocery_result


def render_create_weekly_plan() -> None:
    st.subheader("Create weekly plan")
    st.caption("Pick your meals, then get a grocery list.")
    st.markdown("**Steps:** 1. Meals → 2. Grocery list")

    _invalidate_stale_grocery_result()

    if not _render_weekly_plan_entry():
        return

    db = get_db()
    all_recipes = cached_query_recipes(db)

    current_plan = render_meals_section(db, all_recipes=all_recipes)

    render_grocery_list_section(
        db,
        all_recipes=all_recipes,
        current_plan=current_plan,
    )
