"""Tests for meal-plan status Streamlit helpers (pure logic)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    DEFAULT_MEAL_PLAN_STATUS_COLUMN,
    MEAL_PLAN_STATUS_OPTIONS,
    STATUS_ACTIVE,
    STATUS_PAUSED,
)
from src.grocery_wizard.ui.meal_plan_status_ui import (
    meal_plan_status_apply_key,
    meal_plan_status_editor_context,
    meal_plan_status_select_key,
    meal_plan_status_unavailable_message,
    try_update_meal_plan_status,
)


def _recipe(name: str, *, status: str | None = None) -> Recipe:
    props: dict = {}
    if status is not None:
        props[DEFAULT_MEAL_PLAN_STATUS_COLUMN] = status
    return Recipe(page_id=f"id-{name}", name=name, link=None, ingredients=None, properties=props)


def _mock_db(*, columns: dict | None = None) -> MagicMock:
    db = MagicMock()
    db._config.meal_plan_status_column = None
    default_columns = {
        DEFAULT_MEAL_PLAN_STATUS_COLUMN: MagicMock(type="select"),
    }
    db.schema.all_columns = columns if columns is not None else default_columns
    db.get_select_options.return_value = list(MEAL_PLAN_STATUS_OPTIONS)
    return db


def test_meal_plan_status_editor_context_returns_canonical_options() -> None:
    db = _mock_db()
    context = meal_plan_status_editor_context(db)
    assert context is not None
    assert context.column_name == DEFAULT_MEAL_PLAN_STATUS_COLUMN
    assert context.options == MEAL_PLAN_STATUS_OPTIONS


def test_meal_plan_status_unavailable_when_column_missing() -> None:
    db = _mock_db(columns={})
    message = meal_plan_status_unavailable_message(db)
    assert message is not None
    assert DEFAULT_MEAL_PLAN_STATUS_COLUMN in message


def test_meal_plan_status_unavailable_when_wrong_type() -> None:
    db = _mock_db(
        columns={DEFAULT_MEAL_PLAN_STATUS_COLUMN: MagicMock(type="rich_text")},
    )
    message = meal_plan_status_unavailable_message(db)
    assert message is not None
    assert "select or status" in message


def test_widget_keys_stable_per_recipe_and_scope() -> None:
    assert meal_plan_status_select_key("review", "Soup") == meal_plan_status_select_key(
        "review", "soup"
    )
    assert meal_plan_status_select_key("review", "A") != meal_plan_status_select_key("review", "B")
    assert meal_plan_status_select_key("review", "A") != meal_plan_status_select_key(
        "maintenance", "A"
    )
    assert meal_plan_status_apply_key("review", "Soup") != meal_plan_status_select_key(
        "review", "Soup"
    )


def test_try_update_meal_plan_status_skips_unchanged() -> None:
    db = _mock_db()
    context = meal_plan_status_editor_context(db)
    assert context is not None
    recipe = _recipe("Soup", status=STATUS_ACTIVE)
    updated = try_update_meal_plan_status(
        db,
        recipe,
        new_status=STATUS_ACTIVE,
        context=context,
    )
    assert updated is False
    db.update_recipe.assert_not_called()


def test_try_update_meal_plan_status_writes_when_changed() -> None:
    db = _mock_db()
    context = meal_plan_status_editor_context(db)
    assert context is not None
    recipe = _recipe("Soup", status=STATUS_ACTIVE)
    updated = try_update_meal_plan_status(
        db,
        recipe,
        new_status=STATUS_PAUSED,
        context=context,
    )
    assert updated is True
    db.update_recipe.assert_called_once_with(
        recipe.page_id,
        {DEFAULT_MEAL_PLAN_STATUS_COLUMN: STATUS_PAUSED},
    )
