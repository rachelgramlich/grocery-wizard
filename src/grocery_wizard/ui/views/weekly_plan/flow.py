"""Orchestrates the Create weekly plan page."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, notion_cache_generation
from src.grocery_wizard.ui.views.weekly_plan.grocery_list_ui import render_grocery_list_section
from src.grocery_wizard.ui.views.weekly_plan.plan_entry import (
    _ensure_plan_session_defaults,
    _render_meal_count_input,
    _render_plan_meal_count_continue,
    _render_weekly_plan_entry,
    _sync_plan_length_to_meal_count,
    render_meals_section,
)
from src.grocery_wizard.ui.views.weekly_plan.state import (
    _current_plan_names,
    _invalidate_stale_grocery_result,
    _plan_meals_builder_unlocked,
)
from src.grocery_wizard.ui.views.weekly_plan.step_ui import (
    WeeklyRailStep,
    render_weekly_scroll_into_view,
    render_weekly_step_rail,
    weekly_plan_has_started,
    weekly_step_block,
)

_WEEKLY_RECIPES_WARM_GENERATION_KEY = "_weekly_plan_recipes_warm_generation"


def _weekly_recipes_warm_for_current_cache() -> bool:
    return st.session_state.get(_WEEKLY_RECIPES_WARM_GENERATION_KEY) == notion_cache_generation()


def _load_weekly_plan_recipes(db: NotionRecipesDB) -> list[Recipe]:
    recipes = cached_query_recipes(db)
    st.session_state[_WEEKLY_RECIPES_WARM_GENERATION_KEY] = notion_cache_generation()
    return recipes


def _warm_weekly_plan_recipes_quiet(db: NotionRecipesDB) -> list[Recipe]:
    """Load Notion recipes + meal caches with no loading UI (issue #386)."""
    if _weekly_recipes_warm_for_current_cache():
        return cached_query_recipes(db)
    return _load_weekly_plan_recipes(db)


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
    _invalidate_stale_grocery_result()
    recipe_names = _current_plan_names()
    db = get_db()
    cached_recipes: list[Recipe] | None = None

    def _recipes_for_weekly_plan() -> list[Recipe]:
        nonlocal cached_recipes
        if cached_recipes is not None:
            return cached_recipes
        cached_recipes = _warm_weekly_plan_recipes_quiet(db)
        return cached_recipes

    if not weekly_plan_has_started():
        with weekly_step_block(WeeklyRailStep.GET_STARTED, recipe_names=recipe_names):
            if not _render_weekly_plan_entry():
                return
        return

    render_weekly_step_rail(recipe_names=recipe_names)

    with weekly_step_block(
        WeeklyRailStep.GET_STARTED, recipe_names=recipe_names
    ) as show_get_started:
        if show_get_started and not _render_weekly_plan_entry():
            return

    _ensure_plan_session_defaults()

    with weekly_step_block(WeeklyRailStep.PLAN_MEALS, recipe_names=recipe_names) as show_plan_meals:
        if show_plan_meals:
            meal_count = _render_meal_count_input()
            if not _plan_meals_builder_unlocked():
                _warm_weekly_plan_recipes_quiet(db)
            if _render_plan_meal_count_continue(meal_count=meal_count):
                _sync_plan_length_to_meal_count(meal_count)
                all_recipes = _recipes_for_weekly_plan()
                _weekly_plan_meals_fragment(db, all_recipes, meal_count=meal_count)

    with weekly_step_block(WeeklyRailStep.GROCERY_LIST, recipe_names=recipe_names) as show_grocery:
        if show_grocery:
            _weekly_plan_grocery_fragment(db, _recipes_for_weekly_plan())

    render_weekly_scroll_into_view()
