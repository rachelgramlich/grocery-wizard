"""Notion view helpers for Recipe maintenance."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.integrations.notion_views import (
    ensure_manual_backfill_notion_view_url,
    manual_backfill_notion_filter,
)


def _schema() -> DatabaseSchema:
    meal = ColumnInfo(name="Meal", type="select", options=["Dinner"])
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        instructions_column=None,
        filter_columns=[meal],
        checkbox_columns=[],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Meal": meal,
        },
    )


def test_manual_backfill_notion_filter_and_link() -> None:
    filt = manual_backfill_notion_filter(_schema())
    assert filt == {
        "and": [
            {"property": "Link", "url": {"is_empty": True}},
            {"property": "Ingredients", "rich_text": {"is_empty": True}},
        ],
    }


def test_ensure_manual_backfill_notion_view_url_reuses_named_view() -> None:
    db = MagicMock()
    db._database_id = "db-id"
    db._data_source_id = "ds-id"
    db.schema = _schema()
    client = MagicMock()
    db._client = client
    client.views.list.return_value = {"results": [{"id": "view-1"}]}
    client.views.retrieve.return_value = {
        "id": "view-1",
        "name": "Grocery Wizard — manual backfill",
    }
    client.views.update.return_value = {
        "url": "https://app.notion.com/p/example?v=view-1",
    }

    url = ensure_manual_backfill_notion_view_url(db)

    assert url == "https://app.notion.com/p/example?v=view-1"
    client.views.create.assert_not_called()
    client.views.update.assert_called_once()
