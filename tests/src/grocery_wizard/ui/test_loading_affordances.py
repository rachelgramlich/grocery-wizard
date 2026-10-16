"""Regression tests for shared loading affordances (issue #297)."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT, ui_source


def test_app_mounts_global_loading_banner() -> None:
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "mount_global_loading_banner" in app_text
    assert "loading_indicator" in app_text
    loading_source = (UI_ROOT / "loading.py").read_text(encoding="utf-8")
    mount_fn = loading_source.split("def mount_global_loading_banner", 1)[1].split("\ndef ", 1)[0]
    assert "clear_global_loading_banner()" in mount_fn
    clear_fn = loading_source.split("def clear_global_loading_banner", 1)[1].split("\ndef ", 1)[0]
    assert "GW_BUSY_MESSAGE_KEY" in clear_fn
    assert "_refresh_global_banner()" in clear_fn


def test_long_actions_use_loading_indicator() -> None:
    source = ui_source()
    assert "Building your meal plan" in source
    assert "Preparing ingredient review" in source
    assert "Building grocery list" in source
    assert "Refreshing from Notion" in source
    assert "loading_indicator" in source
    assert "st.spinner" not in source


def test_loading_indicator_uses_spinner_without_inline_progress() -> None:
    loading_source = (UI_ROOT / "loading.py").read_text(encoding="utf-8")
    assert "st.spinner" in loading_source
    assert "st.progress" not in loading_source
    assert "_can_update_global_banner()" in loading_source
    fn_body = loading_source.split("def loading_indicator", 1)[1].split("\ndef ", 1)[0]
    assert "use_global_banner" in fn_body
    assert "if use_global_banner and _can_update_global_banner():" in fn_body
    assert fn_body.count("with st.spinner(message):") == 1


def test_add_recipe_slow_paths_use_loading_indicator() -> None:
    add_recipe = (UI_ROOT / "views" / "add_recipe.py").read_text(encoding="utf-8")
    assert "Fetching recipe from URL" in add_recipe
    assert "Saving recipe to Notion" in add_recipe
    assert "loading_indicator" in add_recipe


def test_meal_plan_regenerate_and_fill_use_loading_indicator() -> None:
    source = ui_source()
    assert "Re-generating your meal plan" in source
    assert "Filling remaining meal slots" in source
    assert "Updating your meals" in source
