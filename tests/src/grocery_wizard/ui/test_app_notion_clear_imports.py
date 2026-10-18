"""Regression: Streamlit entry and Notion cache-clear helpers stay importable (#414)."""

from __future__ import annotations

import importlib


def test_notion_integration_modules_export_clear_cache_helpers() -> None:
    from src.grocery_wizard.integrations import notion_table, notion_views

    assert callable(notion_table.clear_notion_database_metadata_cache)
    assert callable(notion_views.clear_notion_view_url_cache)
    assert "clear_notion_database_metadata_cache" in notion_table.__all__
    assert "clear_notion_view_url_cache" in notion_views.__all__


def test_streamlit_app_module_imports_without_top_level_clear_helpers() -> None:
    """App startup must not depend on integration clear helpers at import time."""
    app = importlib.import_module("src.grocery_wizard.ui.app")
    assert callable(app._refresh_notion_cache_from_ui)
