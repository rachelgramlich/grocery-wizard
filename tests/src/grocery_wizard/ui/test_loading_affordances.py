"""Regression tests for shared loading affordances (issue #297)."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT, ui_source


def test_app_mounts_global_loading_banner() -> None:
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "mount_global_loading_banner" in app_text
    assert "loading_indicator" in app_text


def test_long_actions_use_loading_indicator() -> None:
    source = ui_source()
    assert "Building your meal plan" in source
    assert "Preparing ingredient review" in source
    assert "Building grocery list" in source
    assert "Refreshing from Notion" in source
    assert "loading_indicator" in source
    assert "st.spinner" not in source


def test_add_recipe_slow_paths_use_loading_indicator() -> None:
    add_recipe = (UI_ROOT / "pages" / "add_recipe.py").read_text(encoding="utf-8")
    assert "Fetching recipe from URL" in add_recipe
    assert "Saving recipe to Notion" in add_recipe
    assert "loading_indicator" in add_recipe


def test_meal_plan_regenerate_and_fill_use_loading_indicator() -> None:
    source = ui_source()
    assert "Re-generating your meal plan" in source
    assert "Filling remaining meal slots" in source
    assert "Updating your meals" in source
