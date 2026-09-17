"""Regression tests for issue #29 weekly plan swap UI in app.py."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT, ui_source

APP_FILE = str(APP_PATH)


def test_weekly_plan_has_per_meal_swap_buttons() -> None:
    source = ui_source()
    assert '"Swap"' in source
    assert 'key=f"swap_meal_{index}"' in source
    assert "meal_col, swap_col = st.columns([8, 1])" in source
    assert "_apply_plan_swap" in source
    assert "replace_meals_in_plan(" in source


def test_weekly_plan_regenerate_preserves_rejected_names() -> None:
    source = ui_source()
    assert 'st.button("Re-generate all meals"' in source
    assert "plan_rejected_names" in source
    assert "st.session_state.plan_rejected_names = []" in source


def test_weekly_plan_has_no_bulk_edit_manually_expander() -> None:
    source = ui_source()
    assert 'st.expander("Edit manually"' not in source
    assert 'key="plan_meals_text"' not in source
    assert "_write_plan_names" in source


def test_scratch_plan_slot_first_manual_picker() -> None:
    source = ui_source()
    assert "Choose recipe manually" in source
    assert "_render_slot_manual_picker" in source
    assert "plan_prebuild_filter" in source
    assert (
        "week_level_plan_filter_columns"
        not in source.split("def _render_generate_plan_controls", 1)[1].split(
            "def _render_built_plan_meals", 1
        )[0]
    )
    assert "Keep these recipes" not in source
    assert 'st.expander("More options"' not in source
    assert "Fill remaining slots" in source


def test_manual_picker_recipe_first_then_or_filter() -> None:
    """Issue #220: direct recipe pick before optional per-slot filters."""
    source = ui_source()
    manual = source.split("def _slot_manual_picker_fragment", 1)[1].split(
        "def _render_slot_manual_picker", 1
    )[0]
    assert "plan_slot_direct_pick_" in manual
    assert 'st.markdown("**Or filter**")' in manual
    assert "_render_filtered_recipe_picker" in manual
    assert "st.divider()" in manual
    assert manual.index("_render_direct_recipe_pick") < manual.index('st.markdown("**Or filter**")')
    assert manual.index("_render_filtered_recipe_picker") > manual.index(
        'st.markdown("**Or filter**")'
    )


def test_meal_plan_ingredient_filter_before_checkboxes() -> None:
    """Ingredients multiselect matches other filters and sits above checkbox toggles."""
    filters_source = (UI_ROOT / "meal_plan_filters.py").read_text(encoding="utf-8")
    filters_source = filters_source.split("def render_meal_plan_filters", 1)[1]
    assert "ingredients in your recipes - search to narrow the list" in filters_source
    assert "_ingredient_search" not in filters_source
    assert "Start typing above" not in filters_source
    assert filters_source.index('key=f"{key_prefix}_ingredient_names"') < filters_source.index(
        "for column in checkbox_columns"
    )


def test_weekly_plan_build_shows_per_meal_swap() -> None:
    """AppTest smoke test: Build my plan renders per-meal ↺ buttons."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.run(timeout=60)

    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan entry Continue button missing"
    continue_buttons[0].click().run(timeout=60)

    build_buttons = [b for b in at.button if b.label == "Build my plan"]
    assert build_buttons, "Build my plan button missing"
    build_buttons[0].click().run(timeout=60)

    swap_buttons = [b for b in at.button if b.label == "Swap"]
    assert len(swap_buttons) >= 1, "Expected at least one per-meal Swap button"

    regen = [b for b in at.button if b.label == "Re-generate all meals"]
    assert regen, "Re-generate all meals button missing"

    expander_labels = [e.label for e in at.expander]
    assert "Edit manually" not in expander_labels
    assert "Swap or edit meals" not in expander_labels

    multiselect_labels = [m.label for m in at.multiselect]
    assert "Meals to replace" not in multiselect_labels

    swap_selected = [b for b in at.button if b.label == "Swap selected"]
    assert not swap_selected


def test_dev_mode_exposes_collapsed_dev_tools_expander() -> None:
    source = ui_source()
    assert "_render_dev_jump_tools(db)" in source
    assert 'st.expander("Dev tools", expanded=False)' in source
    assert '_weekly_plan_mode() != "dev"' in source
    assert "commit_dev_jump" in source
    assert "pick_default_recipe_names" in source
    assert "Meals filled: auto" in source
    assert "Meals filled: manual" in source
    assert 'key="dev_jump_manual_recipes"' in source
    assert 'st.markdown("#### Meals filled")' not in source
    assert '"Choose recipes manually"' in source
    assert '"Final list"' in source
    dev_section = source.split('st.expander("Dev tools"', 1)[1].split(
        "def _render_weekly_plan_entry", 1
    )[0]
    assert "DEV_JUMP_FLOW_ORDER" in dev_section
    assert "for step in DEV_JUMP_FLOW_ORDER:\n            _dev_jump_bullet(step)" in dev_section
    bullets_end = dev_section.index("all_names = sorted")
    assert dev_section.index("for step in DEV_JUMP_FLOW_ORDER") < bullets_end
    assert dev_section.index("Meals filled: auto") < dev_section.index('label="Pre-build grocery"')
    assert dev_section.index('label="Pre-build grocery"') < dev_section.index(
        'label="Per-recipe review"'
    )
    assert dev_section.index('label="Per-recipe review"') < dev_section.index('label="Final list"')


def test_post_build_collapses_generate_controls() -> None:
    source = ui_source()
    assert 'st.expander("Adjust filters or rebuild plan", expanded=False)' in source
    assert "plan_last_week_filters" in source


def test_weekly_tab_step_caption() -> None:
    source = ui_source()
    assert "**Steps:** 1. Meals → 2. Grocery list" in source


def test_dev_mode_auto_continues_without_continue_button() -> None:
    source = ui_source()
    entry = source.split("def _render_weekly_plan_entry", 1)[1].split(
        "def _ensure_plan_session_defaults", 1
    )[0]
    assert 'if choice == "dev":' in entry
    assert "plan_meal_count = 1" in entry
    assert entry.index('if choice == "dev":') < entry.index("weekly_plan_mode_continue")


def test_weekly_plan_mode_choices_always_includes_dev() -> None:
    source = (UI_ROOT / "sections" / "weekly_plan" / "state.py").read_text(encoding="utf-8")
    choices_fn = source.split("def _weekly_plan_mode_choices", 1)[1].split(
        "def _weekly_plan_mode", 1
    )[0]
    assert "return _WEEKLY_PLAN_MODES" in choices_fn
    assert "dev_ui_enabled" not in choices_fn


def test_dev_mode_default_meal_count() -> None:
    source = ui_source()
    assert '_weekly_plan_mode() == "dev"' in source
    assert 'key="plan_meal_count"' in source


def test_prebuild_recipe_picker_before_build_my_plan() -> None:
    """Issue #223: single pre-build manual expander; no pin multiselect or week filter row."""
    source = ui_source()
    generate = source.split("def _render_generate_plan_controls", 1)[1].split(
        "def _render_built_plan_meals", 1
    )[0]
    prebuild = source.split("def _render_prebuild_recipe_picker", 1)[1].split(
        "def _set_plan_slot_recipe", 1
    )[0]
    assert "_render_prebuild_recipe_picker" in generate
    assert "_clamp_prebuild_pinned_recipes" in source
    assert "_render_filtered_recipe_picker" in source
    assert "Pin this recipe" in source
    assert "**Pinned meals**" in source
    assert "plan_prebuild_filter" in prebuild
    assert "Pin recipes before building" not in generate
    assert "plan_week_filter" not in generate
    build_idx = generate.index('key="build_plan"')
    picker_idx = generate.index("_render_prebuild_recipe_picker(")
    assert picker_idx < build_idx
    assert 'with st.expander("Choose recipe manually"' in prebuild
    assert "_render_direct_recipe_pick" in prebuild
    assert "plan_prebuild_direct_pick" in prebuild
    assert prebuild.index("_render_direct_recipe_pick") < prebuild.index(
        "_render_filtered_recipe_picker"
    )
    assert (
        "plan_prebuild_pinned_recipes" in source.split("def _locked_recipes_for_plan_build", 1)[1]
    )


def test_post_build_slot_manual_picker_caption() -> None:
    source = ui_source()
    slot = source.split("def _render_slot_manual_picker", 1)[1].split(
        "def _render_dev_jump_tools", 1
    )[0]
    assert "Filters apply to this meal slot only." in slot


def test_grocery_list_extra_items_before_create_button() -> None:
    """Issue #121 / #131: Extra items in their own expander before Create grocery list."""
    source = ui_source()
    section = source.split("### 2. Grocery list", 1)[1].split("def _render_grocery_result", 1)[0]

    create_idx = section.index('if st.button("Create grocery list"')
    assert 'with st.expander("Pantry & Recurring Items"' in section
    assert 'with st.expander("Add extra items"' in section
    extras_block = section.split('with st.expander("Add extra items"', 1)[1].split(
        'if st.button("Create grocery list"', 1
    )[0]
    assert "_grocery_pre_extra_items_widget_key()" in extras_block
    assert section.index('with st.expander("Add extra items"') < create_idx
    pantry_block = section.split('with st.expander("Pantry & Recurring Items"', 1)[1].split(
        'with st.expander("Add extra items"', 1
    )[0]
    assert "_grocery_pre_extra_items_widget_key()" not in pantry_block
