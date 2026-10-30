"""Shared Notion env helpers for pytest (CI uses placeholder credentials)."""

from __future__ import annotations

import os

PYTEST_NOTION_API_KEY_PLACEHOLDER = "pytest-notion-integration-test-key"

# GitHub Actions and local live tests against the CI workspace use NOTION_CI_* paste targets.
# Map into standard NOTION_* names that load_config() expects (prod .env stays NOTION_* only).
_NOTION_CI_TO_STANDARD: tuple[tuple[str, str], ...] = (
    ("NOTION_CI_API_KEY", "NOTION_API_KEY"),
    ("NOTION_CI_RECIPE_DATABASE_ID", "NOTION_RECIPE_DATABASE_ID"),
    ("NOTION_CI_PANTRY_DATABASE_ID", "NOTION_PANTRY_DATABASE_ID"),
    ("NOTION_CI_RECURRING_WEEKLY_DATABASE_ID", "NOTION_RECURRING_WEEKLY_DATABASE_ID"),
    ("NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID", "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID"),
    ("NOTION_CI_DATA_SOURCE_ID", "NOTION_DATA_SOURCE_ID"),
)


def apply_notion_ci_env_for_live_tests() -> None:
    """Copy NOTION_CI_* into NOTION_* when testing the CI workspace locally.

    Skips when GitHub Actions already mapped job env, or when a real prod NOTION_API_KEY is set.
    """
    if not os.environ.get("NOTION_CI_API_KEY"):
        return
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return
    api_key = os.environ.get("NOTION_API_KEY", "")
    if api_key and api_key != PYTEST_NOTION_API_KEY_PLACEHOLDER:
        return
    for ci_key, standard_key in _NOTION_CI_TO_STANDARD:
        value = os.environ.get(ci_key)
        if value:
            os.environ[standard_key] = value


def live_notion_smoke_enabled() -> bool:
    """True when real Notion credentials are configured (not CI pytest placeholders)."""
    apply_notion_ci_env_for_live_tests()
    key = os.environ.get("NOTION_API_KEY", "")
    if key and key != PYTEST_NOTION_API_KEY_PLACEHOLDER:
        return True
    ci_key = os.environ.get("NOTION_CI_API_KEY", "")
    return bool(ci_key) and ci_key != PYTEST_NOTION_API_KEY_PLACEHOLDER
