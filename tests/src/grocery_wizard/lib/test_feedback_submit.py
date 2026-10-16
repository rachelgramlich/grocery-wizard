"""Tests for feedback routing."""

from __future__ import annotations

import pytest

from src.grocery_wizard.config import Config
from src.grocery_wizard.lib.feedback_submit import submit_feedback


def _config(**overrides: object) -> Config:
    base = {
        "notion_api_key": "key",
        "notion_recipe_database_id": "00000000-0000-4000-8000-000000000001",
        "notion_pantry_database_id": "00000000-0000-4000-8000-000000000002",
        "notion_recurring_weekly_database_id": "00000000-0000-4000-8000-000000000003",
        "notion_weekly_meal_plans_database_id": "00000000-0000-4000-8000-000000000004",
    }
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def test_submit_feedback_github_requires_token() -> None:
    with pytest.raises(RuntimeError, match="GITHUB_FEEDBACK_TOKEN"):
        submit_feedback("hello", config=_config(github_feedback_token=None))


def test_submit_feedback_github_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.grocery_wizard.lib.feedback_submit.create_feedback_issue",
        lambda *args, **kwargs: {"number": 12},
    )
    outcome = submit_feedback(
        "idea",
        config=_config(github_feedback_token="tok"),
    )
    assert outcome == "github #12"
