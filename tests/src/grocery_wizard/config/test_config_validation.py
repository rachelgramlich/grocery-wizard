"""Config validation helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.grocery_wizard.config import Config, _format_config_validation_error


def test_format_config_validation_error_lists_fields() -> None:
    try:
        Config(
            notion_api_key="",
            notion_recipe_database_id="00000000-0000-4000-8000-000000000001",
            notion_pantry_database_id="00000000-0000-4000-8000-000000000002",
            notion_recurring_weekly_database_id="00000000-0000-4000-8000-000000000003",
            notion_weekly_meal_plans_database_id="00000000-0000-4000-8000-000000000004",
        )
    except ValidationError as exc:
        message = _format_config_validation_error(exc)
        assert "NOTION" in message or "notion_api_key" in message
    else:
        pytest.fail("expected ValidationError")


def test_require_auth_coerces_string_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROCERY_WIZARD_REQUIRE_AUTH", "true")
    cfg = Config(
        notion_api_key="k",
        notion_recipe_database_id="00000000-0000-4000-8000-000000000001",
        notion_pantry_database_id="00000000-0000-4000-8000-000000000002",
        notion_recurring_weekly_database_id="00000000-0000-4000-8000-000000000003",
        notion_weekly_meal_plans_database_id="00000000-0000-4000-8000-000000000004",
    )
    assert cfg.require_auth is True
