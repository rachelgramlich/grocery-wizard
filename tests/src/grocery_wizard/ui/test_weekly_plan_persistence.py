"""Tests for weekly plan entry modes and saved-plan CSV persistence in the UI."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT, ui_source


def test_saved_plan_continue_sets_meal_count_from_loaded_recipes() -> None:
    source = ui_source()
    entry = source.split("def _render_weekly_plan_entry", 1)[1].split(
        "def _ensure_plan_session_defaults", 1
    )[0]
    assert "loaded_recipes = load_plan_recipes" in entry
    assert "plan_meal_count = max(1, len(loaded_recipes))" in entry
    assert "PLAN_MEAL_COUNT_WIDGET_KEY" in entry


def test_plan_save_collapses_rail_expand_override() -> None:
    state_source = (UI_ROOT / "pages" / "weekly_plan" / "state.py").read_text(encoding="utf-8")
    apply_fn = state_source.split("def _apply_weekly_plan_save_result", 1)[1].split(
        "def _persist_weekly_plan_to_notion", 1
    )[0]
    assert "collapse_after_plan_saved_to_notion" in apply_fn
    save_controls = state_source.split("def _render_save_plan_controls", 1)[1].split(
        "def _invalidate_stale_grocery_result", 1
    )[0]
    assert "st.rerun()" in save_controls


def test_create_grocery_clears_rail_override_after_plan_saved() -> None:
    source = (UI_ROOT / "pages" / "weekly_plan" / "grocery_list_ui.py").read_text(encoding="utf-8")
    section = source.split('if st.button("Create grocery list"', 1)[1].split(
        "with loading_indicator", 1
    )[0]
    assert "clear_expanded_step_override" in section


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
    assert "Dev mode (nothing saved to Notion)" in source


def test_create_grocery_auto_saves_plan_if_missing() -> None:
    source = ui_source()
    section = source.split('if st.button("Create grocery list"', 1)[1].split(
        "_start_recipe_review", 1
    )[0]
    assert "_ensure_weekly_plan_saved_before_grocery" in section


def test_explicit_save_plan_button_after_meals() -> None:
    source = ui_source()
    assert 'key="save_weekly_plan"' in source
    save_button = source.split('key="save_weekly_plan"', 1)[0].rsplit("st.button", 1)[1]
    assert 'type="primary"' in save_button
    assert "#### 1c. Save your plan" in source
    assert 'key="weekly_meals_save"' in source
    assert "Replace saved plan for this week" in source
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


def test_dev_mode_skips_notion_rejection_increments() -> None:
    source = ui_source()
    assert "_weekly_plan_persists_tracking_stats_to_notion" in source
    swap = source.split("def _apply_plan_swap", 1)[1].split('st.markdown("#### 1b. Your meals"', 1)[
        0
    ]
    assert "stats_targets and _weekly_plan_persists_tracking_stats_to_notion()" in swap
    regen = source.split('st.button("Re-generate all meals"', 1)[1].split(
        "_write_plan_names(plan)", 1
    )[0]
    assert "stats_targets and _weekly_plan_persists_tracking_stats_to_notion()" in regen
