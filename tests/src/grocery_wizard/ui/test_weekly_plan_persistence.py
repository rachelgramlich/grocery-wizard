"""Tests for weekly plan entry modes and saved-plan CSV persistence in the UI."""

from __future__ import annotations

from ui_source import APP_PATH, ui_source


def test_saved_plan_build_keeps_loaded_recipes_by_default() -> None:
    source = ui_source()
    assert "_locked_recipes_for_plan_build" in source
    assert "locked_for_build = _locked_recipes_for_plan_build" in source


def test_weekly_plan_entry_modes_in_app() -> None:
    source = ui_source()
    assert "_render_weekly_plan_entry" in source
    assert "weekly_plan_mode" in source
    assert "ensure_saved_weekly_plan" in source
    assert "_render_save_plan_controls" in source
    assert "_ensure_weekly_plan_saved_before_grocery" in source
    assert "saved_plan_week_start" in source
    assert "_render_save_week_choice_buttons" in source
    assert "Dev mode (nothing saved)" in source


def test_create_grocery_auto_saves_plan_if_missing() -> None:
    source = ui_source()
    section = source.split('if st.button("Create grocery list"', 1)[1].split("_start_recipe_review", 1)[0]
    assert "_ensure_weekly_plan_saved_before_grocery" in section


def test_explicit_save_plan_button_after_meals() -> None:
    source = ui_source()
    assert 'key="save_weekly_plan"' in source
    assert "_render_save_plan_controls(_current_plan_names(), cached_recipes=all_recipes)" in source


def test_weekly_plan_entry_app_test_smoke() -> None:
    """AppTest: mode picker appears before Build my plan."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)

    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan entry Continue button missing"

    radios = [r for r in at.radio if r.label == "Weekly plan session"]
    assert radios, "Weekly plan session radio missing"
