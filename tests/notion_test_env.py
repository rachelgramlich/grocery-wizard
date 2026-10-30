"""Shared Notion env helpers for pytest (CI uses placeholder credentials)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from tests.repo_paths import REPO_ROOT

PYTEST_NOTION_API_KEY_PLACEHOLDER = "pytest-notion-integration-test-key"

# Opt in when running live read-only tests against the CI Notion workspace locally.
# GitHub Actions maps NOTION_CI_* → NOTION_* in the workflow; prod Streamlit never uses NOTION_CI_*.
_NOTION_CI_LIVE_ENV = "GROCERY_WIZARD_NOTION_CI_LIVE"

# GitHub paste targets use NOTION_CI_*; map into NOTION_* for load_config() during pytest only.
_NOTION_CI_TO_STANDARD: tuple[tuple[str, str], ...] = (
    ("NOTION_CI_API_KEY", "NOTION_API_KEY"),
    ("NOTION_CI_RECIPE_DATABASE_ID", "NOTION_RECIPE_DATABASE_ID"),
    ("NOTION_CI_PANTRY_DATABASE_ID", "NOTION_PANTRY_DATABASE_ID"),
    ("NOTION_CI_RECURRING_WEEKLY_DATABASE_ID", "NOTION_RECURRING_WEEKLY_DATABASE_ID"),
    ("NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID", "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID"),
    ("NOTION_CI_DATA_SOURCE_ID", "NOTION_DATA_SOURCE_ID"),
)


def _notion_ci_live_explicitly_enabled() -> bool:
    value = os.environ.get(_NOTION_CI_LIVE_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def prime_notion_env_for_pytest() -> None:
    """Load repo ``.env`` into ``os.environ``, then optional CI→standard mapping."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    apply_notion_ci_env_for_live_tests()


def apply_notion_ci_env_for_live_tests() -> None:
    """Copy NOTION_CI_* into NOTION_* when testing the CI workspace locally.

    Requires ``NOTION_CI_API_KEY``. On GitHub Actions the workflow already sets ``NOTION_*``.
    With ``GROCERY_WIZARD_NOTION_CI_LIVE=1``, mapping wins over prod ``NOTION_*`` from ``.env``.
    Otherwise mapping runs only when ``NOTION_API_KEY`` is unset or the pytest placeholder.
    """
    if not os.environ.get("NOTION_CI_API_KEY"):
        return
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return
    if _notion_ci_live_explicitly_enabled():
        for ci_key, standard_key in _NOTION_CI_TO_STANDARD:
            value = os.environ.get(ci_key)
            if value:
                os.environ[standard_key] = value
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
