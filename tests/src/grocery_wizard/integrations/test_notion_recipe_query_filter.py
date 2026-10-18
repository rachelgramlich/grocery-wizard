"""Recipe list queries request only properties the app reads."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.config import Config
from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema, NotionRecipesDB


def _db(*, filter_columns: list[ColumnInfo] | None = None) -> NotionRecipesDB:
    filter_columns = filter_columns or [
        ColumnInfo(name="Meal", type="select", options=["Dinner"]),
        ColumnInfo(name="Meal plan status", type="status", options=["Active"]),
    ]
    schema = DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        filter_columns=filter_columns,
        checkbox_columns=[ColumnInfo(name="Weeknight", type="checkbox")],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Meal": filter_columns[0],
            "Meal plan status": filter_columns[1],
            "Weeknight": ColumnInfo(name="Weeknight", type="checkbox"),
            "Selection count": ColumnInfo(name="Selection count", type="number"),
        },
    )
    config = Config.model_construct(
        notion_api_key="secret",
        notion_recipe_database_id="db-id",
        notion_pantry_database_id="pantry-id",
        notion_recurring_weekly_database_id="recurring-id",
        notion_weekly_meal_plans_database_id="plans-id",
    )
    db = NotionRecipesDB.__new__(NotionRecipesDB)
    db._client = MagicMock()
    db._database_id = "db-id"
    db._config = config
    db._data_source_id = "ds-id"
    db.schema = schema
    return db


def test_query_recipes_passes_filter_properties() -> None:
    db = _db()
    db._client.data_sources.query.return_value = {"results": [], "has_more": False}

    db.query_recipes()

    kwargs = db._client.data_sources.query.call_args.kwargs
    assert kwargs["data_source_id"] == "ds-id"
    assert kwargs["filter_properties"] == sorted(
        {
            "Name",
            "Link",
            "Ingredients",
            "Meal",
            "Meal plan status",
            "Weeknight",
            "Selection count",
        }
    )


def test_query_recipes_edited_since_passes_filter_and_properties() -> None:
    db = _db()
    db._client.data_sources.query.return_value = {"results": [], "has_more": False}

    from datetime import UTC, datetime

    db.query_recipes_edited_since(datetime(2026, 1, 1, tzinfo=UTC))

    kwargs = db._client.data_sources.query.call_args.kwargs
    assert "filter" in kwargs
    assert kwargs["filter"]["timestamp"] == "last_edited_time"
    assert kwargs["filter_properties"]
