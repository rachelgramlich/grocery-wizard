"""Shared Notion env helpers for pytest (CI uses placeholder credentials)."""

from __future__ import annotations

import os

PYTEST_NOTION_API_KEY_PLACEHOLDER = "pytest-notion-integration-test-key"


def live_notion_smoke_enabled() -> bool:
    """True when real Notion credentials are configured (not CI pytest placeholders)."""
    key = os.environ.get("NOTION_API_KEY", "")
    return bool(key) and key != PYTEST_NOTION_API_KEY_PLACEHOLDER
