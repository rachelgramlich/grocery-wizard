"""Tests for Notion weekly plan saves (ensure_plan)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB
from src.grocery_wizard.integrations.notion_table import NotionPageRow


@patch("src.grocery_wizard.integrations.notion_household.NotionRecipesDB")
@patch("src.grocery_wizard.integrations.notion_household.NotionDatabase")
def test_ensure_plan_writes_without_version_column(
    mock_notion_db: MagicMock,
    mock_recipes_db: MagicMock,
) -> None:
    db_instance = MagicMock()
    db_instance.column_types = {
        "Name": "title",
        "Week start": "date",
        "Recipes": "relation",
    }
    db_instance.query_all_pages.return_value = []
    db_instance.property_payload.side_effect = lambda column, value: {column: value}
    week_start = "2026-10-11"
    plan_name = f"{week_start}_plan"

    def _read(row: NotionPageRow, column: str) -> object:
        if column == "Name":
            return plan_name
        if column == "Week start":
            return week_start
        if column == "Recipes":
            return ["recipe-a"]
        return None

    db_instance.read.side_effect = _read
    db_instance.create_page.return_value = NotionPageRow(page_id="plan-page", properties={})
    mock_notion_db.return_value = db_instance

    recipes_db = MagicMock()
    recipes_db.query_recipes.return_value = [
        Recipe(
            page_id="recipe-a",
            name="Pasta",
            link=None,
            ingredients=None,
            properties={},
        ),
    ]
    mock_recipes_db.return_value = recipes_db

    plans_db = NotionWeeklyPlansDB.__new__(NotionWeeklyPlansDB)
    plans_db._db = db_instance
    plans_db._recipes_db = recipes_db

    result = plans_db.ensure_plan(
        ["Pasta"],
        reference_date=date(2026, 10, 8),
    )

    db_instance.create_page.assert_called_once()
    props = db_instance.create_page.call_args[0][0]
    assert "Version" not in props
    assert props["Name"] == plan_name
    assert result.outcome == "created"
    assert result.plan.name == plan_name
