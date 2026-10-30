"""Tests for pytest Notion env helpers (NOTION_* vs NOTION_CI_*)."""

from __future__ import annotations

import os

import pytest

from tests.notion_test_env import (
    PYTEST_NOTION_API_KEY_PLACEHOLDER,
    apply_notion_ci_env_for_live_tests,
)


@pytest.fixture(autouse=True)
def _clear_notion_ci_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROCERY_WIZARD_NOTION_CI_LIVE", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


def test_apply_notion_ci_skips_when_prod_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "prod-key")
    monkeypatch.setenv("NOTION_RECIPE_DATABASE_ID", "prod-recipe-id")
    monkeypatch.setenv("NOTION_CI_RECIPE_DATABASE_ID", "ci-recipe-id")
    apply_notion_ci_env_for_live_tests()
    assert os.environ["NOTION_API_KEY"] == "prod-key"
    assert os.environ["NOTION_RECIPE_DATABASE_ID"] == "prod-recipe-id"


def test_apply_notion_ci_maps_db_ids_when_placeholder_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", PYTEST_NOTION_API_KEY_PLACEHOLDER)
    monkeypatch.setenv("NOTION_CI_RECIPE_DATABASE_ID", "ci-recipe-id")
    apply_notion_ci_env_for_live_tests()
    assert os.environ["NOTION_API_KEY"] == PYTEST_NOTION_API_KEY_PLACEHOLDER
    assert os.environ["NOTION_RECIPE_DATABASE_ID"] == "ci-recipe-id"


def test_apply_notion_ci_overrides_prod_db_when_explicit_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROCERY_WIZARD_NOTION_CI_LIVE", "1")
    monkeypatch.setenv("NOTION_API_KEY", "prod-key")
    monkeypatch.setenv("NOTION_RECIPE_DATABASE_ID", "prod-recipe-id")
    monkeypatch.setenv("NOTION_CI_RECIPE_DATABASE_ID", "ci-recipe-id")
    apply_notion_ci_env_for_live_tests()
    assert os.environ["NOTION_API_KEY"] == "prod-key"
    assert os.environ["NOTION_RECIPE_DATABASE_ID"] == "ci-recipe-id"


def test_apply_notion_ci_skips_on_github_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("NOTION_API_KEY", PYTEST_NOTION_API_KEY_PLACEHOLDER)
    monkeypatch.setenv("NOTION_RECIPE_DATABASE_ID", "workflow-mapped-id")
    monkeypatch.setenv("NOTION_CI_RECIPE_DATABASE_ID", "ci-recipe-id")
    apply_notion_ci_env_for_live_tests()
    assert os.environ["NOTION_RECIPE_DATABASE_ID"] == "workflow-mapped-id"
