"""Tests for NotionDatabase CRUD helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.config import Config
from src.grocery_wizard.integrations import notion_table
from src.grocery_wizard.integrations.notion_table import (
    NOTION_TEXT_BLOCK_MAX_LEN,
    NotionDatabase,
    build_notion_rich_text,
    clear_notion_database_metadata_cache,
    write_notion_property,
)


def _config(*, data_source_id: str | None = "configured-recipe-ds") -> Config:
    return Config.model_construct(
        notion_api_key="secret",
        notion_recipe_database_id="recipe-db",
        notion_pantry_database_id="pantry-db",
        notion_recurring_weekly_database_id="recurring-db",
        notion_weekly_meal_plans_database_id="plans-db",
        notion_data_source_id=data_source_id,
    )


def test_build_notion_rich_text_empty() -> None:
    assert build_notion_rich_text("") == {"rich_text": []}
    assert build_notion_rich_text(None) == {"rich_text": []}


def test_build_notion_rich_text_single_segment() -> None:
    text = "a" * 100
    assert build_notion_rich_text(text) == {"rich_text": [{"text": {"content": text}}]}


def test_build_notion_rich_text_chunks_over_limit() -> None:
    text = "x" * (NOTION_TEXT_BLOCK_MAX_LEN + 448)
    payload = build_notion_rich_text(text)
    segments = payload["rich_text"]
    assert len(segments) == 2
    assert len(segments[0]["text"]["content"]) == NOTION_TEXT_BLOCK_MAX_LEN
    assert len(segments[1]["text"]["content"]) == 448
    assert segments[0]["text"]["content"] + segments[1]["text"]["content"] == text


def test_write_notion_property_rich_text_uses_chunks() -> None:
    text = "y" * (NOTION_TEXT_BLOCK_MAX_LEN * 2 + 1)
    payload = write_notion_property("rich_text", text)
    assert len(payload["rich_text"]) == 3


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


def test_database_handles_share_one_metadata_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Perf guard (#410): building a handle must not re-fetch the data source and schema."""
    client = MagicMock()
    client.data_sources.retrieve.return_value = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(notion_table, "Client", lambda auth: client)
    monkeypatch.setattr(
        notion_table,
        "resolve_notion_data_source_id",
        MagicMock(return_value="pantry-ds"),
    )
    config = _config(data_source_id=None)

    first = NotionDatabase(config, "pantry-db")
    second = NotionDatabase(config, "pantry-db")

    assert first.data_source_id == second.data_source_id == "pantry-ds"
    assert second.column_types == {"Name": "title"}
    assert second.column_types is not first.column_types
    assert notion_table.resolve_notion_data_source_id.call_count == 1
    assert client.data_sources.retrieve.call_count == 1


def test_clearing_metadata_cache_refetches(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.data_sources.retrieve.return_value = {"properties": {}}
    monkeypatch.setattr(notion_table, "Client", lambda auth: client)
    monkeypatch.setattr(
        notion_table,
        "resolve_notion_data_source_id",
        MagicMock(return_value="ds"),
    )
    config = _config(data_source_id=None)

    NotionDatabase(config, "db")
    clear_notion_database_metadata_cache()
    NotionDatabase(config, "db")

    assert client.data_sources.retrieve.call_count == 2
