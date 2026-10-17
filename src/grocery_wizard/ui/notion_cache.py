"""Streamlit ``st.cache_data`` wrappers for Notion reads with explicit invalidation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.planning.saved_weekly_plans import SavedWeeklyPlan, list_saved_plans
from src.grocery_wizard.ui.db_access import get_db

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion_household import PantryEntry

_GENERATION_KEY = "notion_cache_generation"
_SAVED_PLANS_GENERATION_KEY = "notion_saved_plans_generation"
_LAST_RECIPE_LOAD_KEY = "_notion_cache_last_recipe_load_s"
# Notion stamps ``last_edited_time`` to the minute and clocks differ; re-read a little extra.
_HOUSEHOLD_CACHE_GENERATION = 0
_RECIPE_DELTA_OVERLAP = timedelta(minutes=5)


@dataclass
class _RecipeStore:
    """Process-wide recipe copy kept fresh by reading only recently edited pages."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    database_id: str | None = None
    recipes: dict[str, Recipe] | None = None
    synced_at: datetime | None = None
    dirty: bool = False


@st.cache_resource(show_spinner=False)
def _recipe_store() -> _RecipeStore:
    return _RecipeStore()


def notion_cache_generation() -> int:
    if _GENERATION_KEY not in st.session_state:
        st.session_state[_GENERATION_KEY] = 0
    return int(st.session_state[_GENERATION_KEY])


def saved_plans_cache_generation() -> int:
    if _SAVED_PLANS_GENERATION_KEY not in st.session_state:
        st.session_state[_SAVED_PLANS_GENERATION_KEY] = 0
    return int(st.session_state[_SAVED_PLANS_GENERATION_KEY])


def invalidate_saved_plans_cache() -> None:
    """Refresh cached weekly-plan reads without reloading recipes/pantry."""
    st.session_state[_SAVED_PLANS_GENERATION_KEY] = saved_plans_cache_generation() + 1


def invalidate_household_cache() -> None:
    """Drop only pantry and recurring-item reads (a pantry write must not reload recipes)."""
    _load_pantry_cached.clear()
    _load_recurring_cached.clear()


def invalidate_recipes_after_write(*, schema_may_change: bool = False) -> None:
    """Recipe rows changed in Notion: the next read merges only the edited pages.

    Pantry, recurring and saved-plan reads stay cached (a recipe write never changes them).
    Set ``schema_may_change`` when the write can add select options or columns.
    """
    st.session_state[_GENERATION_KEY] = notion_cache_generation() + 1
    store = _recipe_store()
    with store.lock:
        store.dirty = True
    if schema_may_change:
        get_db.clear()


def invalidate_notion_cache() -> None:
    """Drop every cached Notion read (the Refresh button); recipes reload in full."""
    st.session_state[_GENERATION_KEY] = notion_cache_generation() + 1
    invalidate_saved_plans_cache()
    get_db.clear()
    _recipe_store.clear()
    st.cache_data.clear()


def last_recipe_cache_load_seconds() -> float | None:
    """Seconds for the most recent cached recipe load (cache miss only)."""
    value = st.session_state.get(_LAST_RECIPE_LOAD_KEY)
    return float(value) if value is not None else None


def _recipes_from_store(db: NotionRecipesDB) -> list[Recipe]:
    store = _recipe_store()
    with store.lock:
        database_id = db._database_id
        if store.recipes is None or store.database_id != database_id:
            started = datetime.now(UTC)
            store.recipes = {recipe.page_id: recipe for recipe in db.query_recipes()}
            store.database_id = database_id
            store.synced_at = started
            store.dirty = False
        elif store.dirty and store.synced_at is not None:
            started = datetime.now(UTC)
            try:
                changed = db.query_recipes_edited_since(store.synced_at - _RECIPE_DELTA_OVERLAP)
                store.recipes.update({recipe.page_id: recipe for recipe in changed})
            except Exception:
                store.recipes = {recipe.page_id: recipe for recipe in db.query_recipes()}
            store.synced_at = started
            store.dirty = False
        return list(store.recipes.values())


@st.cache_data(show_spinner=False)
def _load_pantry_cached(generation: int, _household_db_id: str) -> list[PantryEntry]:
    del generation
    from src.grocery_wizard.integrations.notion_household import NotionPantryDB

    return NotionPantryDB().list_entries()


@st.cache_data(show_spinner=False)
def _load_recurring_cached(generation: int) -> list[str]:
    del generation
    from src.grocery_wizard.integrations.notion_household import NotionRecurringDB

    return NotionRecurringDB().load_items()


@st.cache_data(show_spinner=False)
def _load_saved_plans_cached(
    weekly_plans_database_id: str,
    saved_plans_generation: int,
    _recipes_db: NotionRecipesDB,
) -> list[SavedWeeklyPlan]:
    del saved_plans_generation
    del weekly_plans_database_id
    recipe_names = {recipe.page_id: recipe.name for recipe in _recipes_from_store(_recipes_db)}
    return list_saved_plans(recipes_db=_recipes_db, recipe_names_by_page_id=recipe_names)


def cached_query_recipes(db: NotionRecipesDB) -> list[Recipe]:
    t0 = time.perf_counter()
    recipes = _recipes_from_store(db)
    elapsed = time.perf_counter() - t0
    if elapsed >= 0.05:
        st.session_state[_LAST_RECIPE_LOAD_KEY] = elapsed
    return recipes


def cached_pantry_entries(*, pantry_database_id: str) -> list[PantryEntry]:
    return _load_pantry_cached(_HOUSEHOLD_CACHE_GENERATION, pantry_database_id)


def cached_pantry_names(*, pantry_database_id: str) -> set[str]:
    entries = cached_pantry_entries(pantry_database_id=pantry_database_id)
    return {entry.name.strip().lower() for entry in entries if entry.name.strip()}


def cached_recurring_items() -> list[str]:
    return list(_load_recurring_cached(_HOUSEHOLD_CACHE_GENERATION))


def cached_saved_plans(
    db: NotionRecipesDB,
    *,
    weekly_plans_database_id: str,
) -> list[SavedWeeklyPlan]:
    return _load_saved_plans_cached(
        weekly_plans_database_id,
        saved_plans_cache_generation(),
        db,
    )


def saved_plan_for_week(
    saved_plans: list[SavedWeeklyPlan],
    week_start: date,
) -> SavedWeeklyPlan | None:
    """Pick the (already de-duplicated) saved plan for a week from the cached list."""
    return next((plan for plan in saved_plans if plan.week_start == week_start), None)


def saved_plan_recipe_names(saved_plans: list[SavedWeeklyPlan], plan_name: str) -> list[str] | None:
    """Recipe names for ``plan_name`` from the cached list, or ``None`` when absent."""
    plan = next((plan for plan in saved_plans if plan.name == plan_name), None)
    return list(plan.recipes) if plan is not None else None
