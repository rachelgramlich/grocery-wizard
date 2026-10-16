"""Tests for feedback routing."""

from __future__ import annotations

from pathlib import Path

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


def test_submit_feedback_local_writes_file(tmp_path: Path) -> None:
    inbox = tmp_path / "feedback_backlog.md"
    outcome = submit_feedback(
        "hello",
        surface="weekly",
        config=_config(feedback_mode="local"),
        local_path=inbox,
    )
    assert outcome == "local"
    assert "hello" in inbox.read_text(encoding="utf-8")


def test_submit_feedback_github_requires_secrets() -> None:
    with pytest.raises(RuntimeError, match="GITHUB_FEEDBACK"):
        submit_feedback("hello", config=_config(feedback_mode="github"))


def test_submit_feedback_github_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.grocery_wizard.lib.feedback_submit.create_feedback_issue",
        lambda *args, **kwargs: {"number": 12},
    )
    outcome = submit_feedback(
        "idea",
        config=_config(
            feedback_mode="github",
            github_feedback_token="tok",
            github_feedback_repository="o/r",
        ),
    )
    assert outcome == "github #12"
