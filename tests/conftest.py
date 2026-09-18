"""Pytest configuration for grocery_wizard tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.notion_test_env import PYTEST_NOTION_API_KEY_PLACEHOLDER

# Dummy Notion settings so CI and fresh clones can run tests without a real `.env`.
# Real credentials from the environment or `.env` take precedence (`setdefault`).
_PYTEST_NOTION_ENV: dict[str, str] = {
    "NOTION_API_KEY": PYTEST_NOTION_API_KEY_PLACEHOLDER,
    "NOTION_RECIPE_DATABASE_ID": "00000000-0000-4000-8000-000000000001",
    "NOTION_PANTRY_DATABASE_ID": "00000000-0000-4000-8000-000000000002",
    "NOTION_RECURRING_WEEKLY_DATABASE_ID": "00000000-0000-4000-8000-000000000003",
    "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID": "00000000-0000-4000-8000-000000000004",
}


def pytest_configure(config: object) -> None:
    del config
    for key, value in _PYTEST_NOTION_ENV.items():
        os.environ.setdefault(key, value)


@pytest.fixture(autouse=True)
def _notion_test_doubles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid live Notion API calls during tests (CI has no integration secrets)."""
    import src.grocery_wizard.shopping.recurring_weekly_items as recurring_mod
    from src.grocery_wizard.integrations.notion import Recipe

    def load_recurring(path: Path | None = None) -> list[str]:
        if path is not None:
            return recurring_mod._load_recurring_from_file(path)
        return []

    monkeypatch.setattr(recurring_mod, "load_recurring_weekly_items", load_recurring)
    monkeypatch.setattr(
        "src.grocery_wizard.ui.grocery_flow.load_recurring_weekly_items",
        load_recurring,
    )
    monkeypatch.setattr(
        "src.grocery_wizard.ui.sections.pantry_recurring.load_recurring_weekly_items",
        load_recurring,
    )

    fake_db = MagicMock()
    fake_db.schema.all_columns = {}
    fake_db.query_recipes.return_value = [
        Recipe(
            page_id="pytest-recipe-1",
            name="Test Soup",
            link=None,
            ingredients="1 cup flour",
            properties={},
        ),
    ]

    def _fake_get_db() -> MagicMock:
        return fake_db

    get_db_targets = (
        "src.grocery_wizard.ui.db_access",
        "src.grocery_wizard.ui.app",
        "src.grocery_wizard.ui.nyt_sync",
        "src.grocery_wizard.ui.sections.add_recipe",
        "src.grocery_wizard.ui.sections.weekly_plan.flow",
        "src.grocery_wizard.ui.sections.weekly_plan.plan_entry",
        "src.grocery_wizard.ui.sections.weekly_plan.grocery_wizard",
        "src.grocery_wizard.ui.sections.weekly_plan.state",
    )
    for module_path in get_db_targets:
        monkeypatch.setattr(f"{module_path}.get_db", _fake_get_db, raising=False)
    monkeypatch.setattr(
        "src.grocery_wizard.ui.notion_cache._load_pantry_cached",
        lambda _generation, _household_db_id: [],
    )
    monkeypatch.setattr(
        "src.grocery_wizard.ui.notion_cache._load_saved_plans_cached",
        lambda _weekly_plans_database_id, _generation, _recipes_db: [],
    )


_UI_TEST_HELPERS = Path(__file__).resolve().parent / "src" / "grocery_wizard" / "ui"
if str(_UI_TEST_HELPERS) not in sys.path:
    sys.path.insert(0, str(_UI_TEST_HELPERS))
