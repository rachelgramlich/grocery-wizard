"""Tests for Notion pantry writes (append_item)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.grocery_wizard.integrations.notion_household import NotionPantryDB


@patch("src.grocery_wizard.integrations.notion_household.NotionDatabase")
def test_append_item_creates_notion_page_with_name_and_aisle(mock_notion_db: MagicMock) -> None:
    db_instance = MagicMock()
    db_instance.column_types = {"Name": "title", "Store Aisle": "select"}
    db_instance.list_entries.return_value = []
    db_instance.property_payload.side_effect = lambda column, value: {
        column: {"title": [{"text": {"content": str(value)}}]}
        if column == "Name"
        else {"select": {"name": str(value)}}
    }
    mock_notion_db.return_value = db_instance

    pantry = NotionPantryDB.__new__(NotionPantryDB)
    pantry._db = db_instance
    pantry._aisle_column = "Store Aisle"

    assert pantry.append_item("soy sauce", section="Dry goods")

    db_instance.create_page.assert_called_once()
    props = db_instance.create_page.call_args[0][0]
    assert props["Name"]["title"][0]["text"]["content"] == "soy sauce"
    assert props["Store Aisle"]["select"]["name"].startswith("Dry goods")
