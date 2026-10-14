"""Regression tests for weekly plan performance UX (issue #207)."""

from __future__ import annotations

from ui_source import UI_ROOT, ui_source


def test_weekly_plan_uses_fragments_for_meals_and_grocery() -> None:
    source = ui_source()
    assert '@st.fragment(key="weekly_plan_meals")' in source
    assert '@st.fragment(key="weekly_plan_grocery")' in source
    assert "_weekly_plan_meals_fragment" in source
    assert "Loading recipes from Notion" in source


def test_meal_slot_manual_picker_uses_per_slot_fragment() -> None:
    source = ui_source()
    assert "_slot_manual_picker_fragment" in source
    assert 'key=f"plan_slot_manual_{slot_index}"' in source


def test_ingredient_filter_single_searchable_multiselect() -> None:
    filters_source = (UI_ROOT / "meal_plan_filters.py").read_text(encoding="utf-8")
    assert "ingredients in your recipes - search to narrow the list" in filters_source
    assert "_ingredient_search" not in filters_source
    render_fn = filters_source.split("def render_meal_plan_filters", 1)[1].split("\ndef ", 1)[0]
    assert "scoped_ingredient_multiselect_options(" in render_fn
    assert "_ingredient_narrow" in render_fn


def test_plan_meals_loads_recipes_before_meal_count_and_dedupes() -> None:
    """Issue #336: show Notion load before meal count; one recipe fetch per rerun."""
    flow_source = (UI_ROOT / "pages" / "weekly_plan" / "flow.py").read_text(encoding="utf-8")
    plan_block = flow_source.split("WeeklyRailStep.PLAN_MEALS", 1)[1].split(
        "WeeklyRailStep.GROCERY_LIST", 1
    )[0]
    assert "_recipes_for_weekly_plan()" in plan_block
    assert plan_block.index("_recipes_for_weekly_plan()") < plan_block.index(
        "_render_meal_count_input()"
    )
    assert plan_block.count("cached_query_recipes(") == 0
    assert flow_source.count("cached_query_recipes(") == 1


def test_prebuild_manual_picker_lazy_when_collapsed() -> None:
    """Issue #336: skip heavy filter widgets until Choose recipe manually is open."""
    source = ui_source()
    prebuild = source.split("def _render_prebuild_recipe_picker", 1)[1].split(
        "def _set_plan_slot_recipe", 1
    )[0]
    assert "PLAN_PREBUILD_MANUAL_EXPANDER_KEY" in prebuild
    assert "_render_filtered_recipe_picker" in prebuild
    assert "if st.session_state.get(PLAN_PREBUILD_MANUAL_EXPANDER_KEY)" in prebuild


def test_long_actions_show_spinners() -> None:
    source = ui_source()
    assert "Building your meal plan" in source
    assert "Preparing ingredient review" in source
    assert "Building grocery list" in source
    refresh_fn = source.split("def _refresh_notion_cache_from_ui", 1)[1].split(
        "def _render_notion_cache_controls", 1
    )[0]
    assert "Refreshing from Notion" in refresh_fn
