"""Tests for Notion meal-plan stats and rotation helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    DEFAULT_MEAL_PLAN_STATUS_COLUMN,
    DEFAULT_REJECTION_COUNT_COLUMN,
    DEFAULT_SELECTION_COUNT_COLUMN,
    STATUS_DEPRECATED,
    STATUS_FAVORITE,
    STATUS_PAUSED,
    filter_recipes_for_auto_suggest,
    increment_plan_selections,
    increment_suggestion_rejections,
    meal_plan_status,
    origins_after_swap,
    pick_weight_rejection_penalty,
    pick_weight_status_multiplier,
    rejection_names_from_swap,
    resolve_slot_origins_for_plan,
    suggestion_rejections_column_name,
)


def _recipe(
    name: str,
    *,
    status: str | None = None,
    rejections: int | None = None,
) -> Recipe:
    props: dict = {}
    if status is not None:
        props[DEFAULT_MEAL_PLAN_STATUS_COLUMN] = status
    if rejections is not None:
        props[DEFAULT_REJECTION_COUNT_COLUMN] = rejections
    return Recipe(page_id=f"id-{name}", name=name, link=None, ingredients=None, properties=props)


def _mock_db(*, columns: dict | None = None) -> MagicMock:
    db = MagicMock()
    db._config.suggestion_rejections_column = None
    db._config.plan_selections_column = None
    db._config.meal_plan_status_column = None
    default_columns = {
        DEFAULT_REJECTION_COUNT_COLUMN: MagicMock(type="number"),
        DEFAULT_SELECTION_COUNT_COLUMN: MagicMock(type="number"),
        DEFAULT_MEAL_PLAN_STATUS_COLUMN: MagicMock(type="select"),
    }
    db.schema.all_columns = columns if columns is not None else default_columns
    return db


def test_resolve_slot_origins_marks_locked_vs_suggested() -> None:
    plan = ["Pinned A", "Auto B", "Auto C"]
    origins = resolve_slot_origins_for_plan(plan, locked_names={"Pinned A"})
    assert origins == ["pinned", "suggested", "suggested"]


def test_rejection_names_only_for_suggested_slots() -> None:
    plan = ["Pin", "Auto"]
    origins = ["pinned", "suggested"]
    rejected = rejection_names_from_swap(plan, ["Pin", "Auto"], origins)
    assert rejected == {"Auto"}


def test_origins_after_swap_marks_replacement_as_suggested() -> None:
    plan = ["A", "B"]
    origins = ["suggested", "suggested"]
    updated = ["C", "B"]
    assert origins_after_swap(plan, ["A"], origins, updated) == ["suggested", "suggested"]


def test_filter_auto_suggest_excludes_paused_and_deprecated() -> None:
    recipes = [
        _recipe("Active"),
        _recipe("Pause", status=STATUS_PAUSED),
        _recipe("Old", status=STATUS_DEPRECATED),
    ]
    filtered = filter_recipes_for_auto_suggest(
        recipes,
        status_column=DEFAULT_MEAL_PLAN_STATUS_COLUMN,
    )
    assert [r.name for r in filtered] == ["Active"]


def test_pick_weight_favorite_and_rejections() -> None:
    favorite = _recipe("Fav", status=STATUS_FAVORITE)
    noisy = _recipe("Noisy", rejections=4)
    assert (
        pick_weight_status_multiplier(favorite, status_column=DEFAULT_MEAL_PLAN_STATUS_COLUMN)
        == 2.0
    )
    assert (
        pick_weight_rejection_penalty(noisy, rejections_column=DEFAULT_REJECTION_COUNT_COLUMN)
        == 3.0
    )


def test_increment_suggestion_rejections_updates_notion() -> None:
    db = _mock_db()
    recipe = _recipe("Soup", rejections=2)
    db.query_recipes.return_value = [recipe]
    updated = increment_suggestion_rejections(db, {"Soup"}, cached_recipes=[recipe])
    assert updated == 1
    db.update_recipe.assert_called_once_with(
        recipe.page_id,
        {DEFAULT_REJECTION_COUNT_COLUMN: 3},
    )


def test_increment_plan_selections_dedupes_names() -> None:
    db = _mock_db()
    recipe = _recipe("Soup")
    recipe.properties[DEFAULT_SELECTION_COUNT_COLUMN] = 1
    db.query_recipes.return_value = [recipe]
    updated = increment_plan_selections(db, ["Soup", "Soup"], cached_recipes=[recipe])
    assert updated == 1
    db.update_recipe.assert_called_once_with(
        recipe.page_id,
        {DEFAULT_SELECTION_COUNT_COLUMN: 2},
    )


def test_suggestion_rejections_column_missing_when_not_in_schema() -> None:
    db = _mock_db(columns={})
    assert suggestion_rejections_column_name(db) is None


def test_meal_plan_status_defaults_to_active() -> None:
    assert meal_plan_status(_recipe("X"), status_column=DEFAULT_MEAL_PLAN_STATUS_COLUMN) == "Active"
