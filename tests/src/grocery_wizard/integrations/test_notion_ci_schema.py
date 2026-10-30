"""Unit tests for Notion CI schema checks (mocked — no live Notion)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.integrations.notion_ci_schema import (
    NotionCiCheckReport,
    collect_pantry_schema_errors,
    collect_recipes_schema_errors,
    collect_recurring_schema_errors,
    collect_weekly_plans_schema_errors,
    format_notion_ci_report,
    run_notion_ci_checks,
    verify_recipe_query_smoke,
)
from src.grocery_wizard.integrations.notion_household import (
    PANTRY_STORE_AISLE_COLUMN,
    PLAN_NAME_COLUMN,
)


def _recipe_schema(*, ingredients: str | None = "Ingredients") -> DatabaseSchema:
    columns = {
        "Name": ColumnInfo(name="Name", type="title"),
        "Link": ColumnInfo(name="Link", type="url"),
    }
    if ingredients:
        columns[ingredients] = ColumnInfo(name=ingredients, type="rich_text")
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column=ingredients,
        filter_columns=[],
        checkbox_columns=[],
        all_columns=columns,
    )


def test_collect_recipes_schema_errors_ok() -> None:
    assert collect_recipes_schema_errors(_recipe_schema()) == []


def test_collect_recipes_schema_errors_missing_ingredients() -> None:
    errors = collect_recipes_schema_errors(_recipe_schema(ingredients=None))
    assert len(errors) == 1
    assert "Ingredients" in errors[0]


def test_collect_pantry_schema_errors_ok() -> None:
    column_types = {"Name": "title", PANTRY_STORE_AISLE_COLUMN: "select"}
    assert collect_pantry_schema_errors(column_types) == []


def test_collect_pantry_schema_errors_missing_aisle() -> None:
    errors = collect_pantry_schema_errors({"Name": "title"})
    assert any("store-aisle" in err for err in errors)


def test_collect_recurring_schema_errors_missing_name() -> None:
    errors = collect_recurring_schema_errors({})
    assert any("Name" in err for err in errors)


def test_collect_weekly_plans_schema_errors_ok() -> None:
    column_types = {
        PLAN_NAME_COLUMN: "title",
        "Week start": "date",
        "Recipes": "relation",
    }
    assert collect_weekly_plans_schema_errors(column_types) == []


def test_verify_recipe_query_smoke_empty_db_note() -> None:
    recipes_db = MagicMock()
    recipes_db.query_recipes.return_value = []
    report = NotionCiCheckReport()
    verify_recipe_query_smoke(recipes_db, report)
    assert report.ok
    assert any("empty" in note for note in report.notes)


def test_verify_recipe_query_smoke_unparseable_pages() -> None:
    from types import SimpleNamespace

    recipes_db = MagicMock()
    recipes_db.query_recipes.return_value = [
        SimpleNamespace(name="  ", ingredients=None),
    ]
    report = NotionCiCheckReport()
    verify_recipe_query_smoke(recipes_db, report)
    assert not report.ok
    assert any("readable name" in err for err in report.errors)


@patch("src.grocery_wizard.integrations.notion_ci_schema.NotionRecipesDB")
@patch("src.grocery_wizard.integrations.notion_ci_schema.NotionDatabase")
def test_run_notion_ci_checks_happy_path(
    notion_database: MagicMock,
    notion_recipes_db: MagicMock,
) -> None:
    notion_recipes_db.return_value.schema = _recipe_schema()
    notion_recipes_db.return_value.query_recipes.return_value = [
        MagicMock(name="Soup", ingredients="1 cup broth"),
    ]

    def _column_types_for_db(_config: object, database_id: str) -> MagicMock:
        handle = MagicMock()
        if database_id == "pantry-id":
            handle.column_types = {"Name": "title", PANTRY_STORE_AISLE_COLUMN: "select"}
        elif database_id == "recurring-id":
            handle.column_types = {"Name": "title"}
        elif database_id == "plans-id":
            handle.column_types = {
                "Name": "title",
                "Week start": "date",
                "Recipes": "relation",
            }
        else:
            pytest.fail(f"unexpected database_id {database_id!r}")
        return handle

    notion_database.side_effect = _column_types_for_db

    config = MagicMock()
    config.notion_recipe_database_id = "recipe-id"
    config.notion_pantry_database_id = "pantry-id"
    config.notion_recurring_weekly_database_id = "recurring-id"
    config.notion_weekly_meal_plans_database_id = "plans-id"

    report = run_notion_ci_checks(config)
    assert report.ok
    assert format_notion_ci_report(report).startswith("Notion CI checks passed.")
