"""Regression tests for Add Recipe three-way entry layout (issue #198)."""

from __future__ import annotations

from ui_source import ui_source


def test_add_recipe_surfaces_three_entry_paths_without_collapsed_expanders() -> None:
    source = ui_source()
    assert "Choose one of three ways to add recipes to Notion." in source
    assert source.count("st.container(border=True)") >= 3
    assert "**Recipe URL**" in source
    assert "**Sync from NYT Cooking**" in source
    assert "Sync all saved recipes from your NYT Cooking recipe-box folder." in source
    assert "**Type it in myself**" in source
    assert 'st.expander("Type it in myself"' not in source
