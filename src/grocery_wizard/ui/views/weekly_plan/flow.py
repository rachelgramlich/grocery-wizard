"""Orchestrates the Create weekly plan page."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, notion_cache_generation
from src.grocery_wizard.ui.views.weekly_plan.grocery_list_ui import render_grocery_list_section
from src.grocery_wizard.ui.views.weekly_plan.plan_entry import (
    _ensure_plan_session_defaults,
    _render_meal_count_input,
    _render_plan_meal_count_continue,
    _render_weekly_plan_entry,
    _sync_plan_length_to_meal_count,
    render_meals_section,
    warm_weekly_plan_meal_caches,
)
from src.grocery_wizard.ui.views.weekly_plan.state import (
    _current_plan_names,
    _invalidate_stale_grocery_result,
)
from src.grocery_wizard.ui.views.weekly_plan.step_ui import (
    WeeklyRailStep,
    render_weekly_scroll_into_view,
    render_weekly_step_rail,
    weekly_plan_has_started,
    weekly_step_block,
)

_WEEKLY_RECIPES_WARM_GENERATION_KEY = "_weekly_plan_recipes_warm_generation"
_WEEKLY_RECIPES_PREFETCH_PAINT_KEY = "_weekly_plan_recipes_prefetch_paint"


def _weekly_recipes_warm_for_current_cache() -> bool:
    return st.session_state.get(_WEEKLY_RECIPES_WARM_GENERATION_KEY) == notion_cache_generation()


def _load_and_warm_weekly_plan_recipes(db: NotionRecipesDB) -> list[Recipe]:
    recipes = cached_query_recipes(db)
    warm_weekly_plan_meal_caches(recipes)
    st.session_state[_WEEKLY_RECIPES_WARM_GENERATION_KEY] = notion_cache_generation()
    return recipes


def _prefetch_weekly_plan_recipes(db: NotionRecipesDB) -> None:
    """Warm Notion recipe + meal-builder caches during Get started (issue #386).

    Streamlit runs synchronously, so we paint step 1 once, ``st.rerun()``, then load
    on the next run while the user is still on Get started.
    """
    if _weekly_recipes_warm_for_current_cache():
        return
    if not st.session_state.get(_WEEKLY_RECIPES_PREFETCH_PAINT_KEY):
        st.session_state[_WEEKLY_RECIPES_PREFETCH_PAINT_KEY] = True
        st.rerun()
    with loading_indicator("Loading recipes from Notion…"):
        _load_and_warm_weekly_plan_recipes(db)


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
        if _weekly_recipes_warm_for_current_cache():
            cached_recipes = cached_query_recipes(db)
            return cached_recipes
        with loading_indicator("Loading recipes from Notion…"):
            cached_recipes = _load_and_warm_weekly_plan_recipes(db)
        return cached_recipes

    if not weekly_plan_has_started():
        with weekly_step_block(WeeklyRailStep.GET_STARTED, recipe_names=recipe_names):
            if not _render_weekly_plan_entry():
                return
        _prefetch_weekly_plan_recipes(db)
        return

    _prefetch_weekly_plan_recipes(db)

    render_weekly_step_rail(recipe_names=recipe_names)

    with weekly_step_block(
        WeeklyRailStep.GET_STARTED, recipe_names=recipe_names
    ) as show_get_started:
        if show_get_started and not _render_weekly_plan_entry():
            return

    _ensure_plan_session_defaults()

    with weekly_step_block(WeeklyRailStep.PLAN_MEALS, recipe_names=recipe_names) as show_plan_meals:
        if show_plan_meals:
            all_recipes = _recipes_for_weekly_plan()
            meal_count = _render_meal_count_input()
            if _render_plan_meal_count_continue(meal_count=meal_count):
                _sync_plan_length_to_meal_count(meal_count)
                _weekly_plan_meals_fragment(db, all_recipes, meal_count=meal_count)

    with weekly_step_block(WeeklyRailStep.GROCERY_LIST, recipe_names=recipe_names) as show_grocery:
        if show_grocery:
            _weekly_plan_grocery_fragment(db, _recipes_for_weekly_plan())

    render_weekly_scroll_into_view()
