"""Tests for NotionDatabase CRUD helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.config import Config
from src.grocery_wizard.integrations.notion_table import NotionDatabase


def _config(*, data_source_id: str | None = "configured-recipe-ds") -> Config:
    return Config.model_construct(
        notion_api_key="secret",
        notion_recipe_database_id="recipe-db",
        notion_pantry_database_id="pantry-db",
        notion_recurring_weekly_database_id="recurring-db",
        notion_weekly_meal_plans_database_id="plans-db",
        notion_data_source_id=data_source_id,
    )


def test_create_page_parents_row_under_data_source() -> None:
    config = _config(data_source_id=None)
    db = NotionDatabase.__new__(NotionDatabase)
    db._config = config
    db._client = MagicMock()
    db._database_id = "pantry-db"
    db._data_source_id = "pantry-ds"
    db.column_types = {"Name": "title"}
    db._client.pages.create.return_value = {
        "id": "page-1",
        "properties": {},
    }

    row = db.create_page({"Name": {"title": [{"text": {"content": "soy sauce"}}]}})

    assert row.page_id == "page-1"
    db._client.pages.create.assert_called_once_with(
        parent={"type": "data_source_id", "data_source_id": "pantry-ds"},
        properties={"Name": {"title": [{"text": {"content": "soy sauce"}}]}},
    )


def test_household_db_ignores_global_notion_data_source_id() -> None:
    config = _config(data_source_id="configured-recipe-ds")
    db = NotionDatabase.__new__(NotionDatabase)
    db._config = config
    db._client = MagicMock()
    db._database_id = "pantry-db"
    db._client.databases.retrieve.return_value = {
        "data_sources": [{"id": "pantry-ds-from-db"}],
    }

    resolved = db._resolve_data_source_id()

    assert resolved == "pantry-ds-from-db"
    db._client.databases.retrieve.assert_called_once_with(database_id="pantry-db")
