"""Meal-plan stat columns must not be auto-classified or metadata-backfilled."""

from __future__ import annotations

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.recipes.classify import classify_recipe
from src.grocery_wizard.recipes.recipe_maintenance import metadata_filter_columns_for_meals
from src.grocery_wizard.recipes.recipe_meal_plan_stats import DEFAULT_MEAL_PLAN_STATUS_COLUMN


def _schema_with_meal_plan_status() -> DatabaseSchema:
    status = ColumnInfo(
        name=DEFAULT_MEAL_PLAN_STATUS_COLUMN,
        type="select",
        options=["Active", "Favorite", "Paused", "Deprecated"],
    )
    meal = ColumnInfo(name="Meal", type="multi_select", options=["Dinner"])
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        filter_columns=[meal, status],
        checkbox_columns=[],
        all_columns={"Meal": meal, DEFAULT_MEAL_PLAN_STATUS_COLUMN: status},
    )


def test_classify_recipe_skips_meal_plan_status() -> None:
    schema = _schema_with_meal_plan_status()
    filter_columns = [(col.name, col.type, col.options) for col in schema.filter_columns]
    result = classify_recipe("Quick Weeknight Chicken", ["chicken"], filter_columns)
    assert DEFAULT_MEAL_PLAN_STATUS_COLUMN not in result


def test_metadata_filter_columns_skip_meal_plan_status() -> None:
    schema = _schema_with_meal_plan_status()
    names = [col.name for col in metadata_filter_columns_for_meals(schema, {"Dinner"})]
    assert DEFAULT_MEAL_PLAN_STATUS_COLUMN not in names
