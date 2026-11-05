"""Shared Notion env helpers for pytest (CI uses placeholder credentials)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from tests.repo_paths import REPO_ROOT

PYTEST_NOTION_API_KEY_PLACEHOLDER = "pytest-notion-integration-test-key"

# Opt in when running live read-only tests against the CI Notion workspace locally.
# GitHub Actions maps NOTION_CI_API_KEY → NOTION_API_KEY and NOTION_CI_*_DATABASE_ID → NOTION_* in job env.
# Prod Streamlit never uses NOTION_CI_* names.
_NOTION_CI_LIVE_ENV = "GROCERY_WIZARD_NOTION_CI_LIVE"

# Local / docs: NOTION_CI_* only for test-workspace database IDs (not API key or data source).
_NOTION_CI_TO_STANDARD: tuple[tuple[str, str], ...] = (
    ("NOTION_CI_RECIPE_DATABASE_ID", "NOTION_RECIPE_DATABASE_ID"),
    ("NOTION_CI_PANTRY_DATABASE_ID", "NOTION_PANTRY_DATABASE_ID"),
    ("NOTION_CI_RECURRING_WEEKLY_DATABASE_ID", "NOTION_RECURRING_WEEKLY_DATABASE_ID"),
    ("NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID", "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID"),
    ("NOTION_CI_DEBUG_LOGS_DATABASE_ID", "NOTION_DEBUG_LOGS_DATABASE_ID"),
)


def _notion_ci_live_explicitly_enabled() -> bool:
    value = os.environ.get(_NOTION_CI_LIVE_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _has_ci_database_ids() -> bool:
    return any(os.environ.get(ci_key) for ci_key, _ in _NOTION_CI_TO_STANDARD)


def _apply_ci_database_id_mapping() -> None:
    for ci_key, standard_key in _NOTION_CI_TO_STANDARD:
        value = os.environ.get(ci_key)
        if value:
            os.environ[standard_key] = value


def _apply_ci_api_key_mapping() -> None:
    ci_key = os.environ.get("NOTION_CI_API_KEY", "").strip()
    if not ci_key:
        return
    if _notion_ci_live_explicitly_enabled():
        os.environ["NOTION_API_KEY"] = ci_key
        return
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key or api_key == PYTEST_NOTION_API_KEY_PLACEHOLDER:
        os.environ["NOTION_API_KEY"] = ci_key


def _apply_debug_logs_database_id_fallback() -> None:
    if os.environ.get("NOTION_DEBUG_LOGS_DATABASE_ID"):
        return
    weekly = os.environ.get("NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID")
    if weekly:
        os.environ["NOTION_DEBUG_LOGS_DATABASE_ID"] = weekly


def _should_use_ci_notion_env() -> bool:
    if not _has_ci_database_ids() and not os.environ.get("NOTION_CI_API_KEY"):
        return False
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return False
    if _notion_ci_live_explicitly_enabled():
        return True
    api_key = os.environ.get("NOTION_API_KEY", "")
    return not api_key or api_key == PYTEST_NOTION_API_KEY_PLACEHOLDER


def prime_notion_env_for_pytest() -> None:
    """Load repo ``.env`` into ``os.environ``, then optional CI→standard mapping."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    apply_notion_ci_env_for_live_tests()


def apply_notion_ci_env_for_live_tests() -> None:
    """Map ``NOTION_CI_*`` secrets into ``NOTION_*`` for CI / Cloud Agent live tests.

    ``NOTION_API_KEY`` and optional ``NOTION_DATA_SOURCE_ID`` use standard names in the app.
    GitHub Actions sets ``NOTION_API_KEY`` and database IDs in workflow env (no mapping here).
    Cursor Cloud Agents and local runs: same secret names as Actions — this helper copies
    ``NOTION_CI_API_KEY`` → ``NOTION_API_KEY`` and CI database IDs → ``NOTION_*`` when
    ``GROCERY_WIZARD_NOTION_CI_LIVE=1``, or when ``NOTION_API_KEY`` is unset / pytest placeholder.
    ``NOTION_DEBUG_LOGS_DATABASE_ID`` falls back to weekly meal plans when unset (matches Actions).
    """
    if not _should_use_ci_notion_env():
        return
    _apply_ci_api_key_mapping()
    if _has_ci_database_ids():
        _apply_ci_database_id_mapping()
    _apply_debug_logs_database_id_fallback()


def live_notion_smoke_enabled() -> bool:
    """True when real Notion credentials are configured (not CI pytest placeholders)."""
    apply_notion_ci_env_for_live_tests()
    key = os.environ.get("NOTION_API_KEY", "")
    return bool(key) and key != PYTEST_NOTION_API_KEY_PLACEHOLDER
