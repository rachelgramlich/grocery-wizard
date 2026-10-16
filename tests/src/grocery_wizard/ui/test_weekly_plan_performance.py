"""Regression tests for weekly plan performance UX (issue #207)."""

from __future__ import annotations

from ui_source import UI_ROOT, ui_source


def test_weekly_plan_uses_fragments_for_meals_and_grocery() -> None:
    source = ui_source()
    assert '@st.fragment(key="weekly_plan_meals")' in source
    assert '@st.fragment(key="weekly_plan_grocery")' in source
    assert "_weekly_plan_meals_fragment" in source
    assert "Preparing your meal builder" in source


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


def test_plan_meals_warms_recipes_quietly_before_meal_count_continue() -> None:
    """Issue #386: no loading UI until meal-count Continue; quiet warm while picking count."""
    flow_source = (UI_ROOT / "views" / "weekly_plan" / "flow.py").read_text(encoding="utf-8")
    plan_block = flow_source.split("WeeklyRailStep.PLAN_MEALS", 1)[1].split(
        "WeeklyRailStep.GROCERY_LIST", 1
    )[0]
    assert "_render_meal_count_input()" in plan_block
    assert "_warm_weekly_plan_recipes_quiet" in plan_block
    assert plan_block.index("_render_meal_count_input()") < plan_block.index(
        "_warm_weekly_plan_recipes_quiet"
    )
    assert plan_block.count("cached_query_recipes(") == 0
    assert flow_source.count("cached_query_recipes(") == 2
    meal_builder_block = plan_block.split("if _render_plan_meal_count_continue", 1)[1]
    assert "loading_indicator" in meal_builder_block
    assert "use_global_banner=False" in meal_builder_block
    assert "_MEAL_BUILDER_LOADING_MESSAGE" in meal_builder_block
    assert "_weekly_plan_meals_fragment" in meal_builder_block.split("loading_indicator", 1)[-1]
    assert "clear_global_loading_banner" in meal_builder_block


def test_prebuild_manual_picker_lazy_when_collapsed() -> None:
    """Issue #336: skip heavy filter widgets until Choose meals manually popover is open."""
    source = ui_source()
    prebuild = source.split("def _render_prebuild_recipe_picker", 1)[1].split(
        "def _set_plan_slot_recipe", 1
    )[0]
    assert "PLAN_PREBUILD_MANUAL_POPOVER_KEY" in prebuild
    assert "_render_filtered_recipe_picker" in prebuild
    assert 'on_change="rerun"' in prebuild
    assert "if manual_popover.open" in prebuild
    assert "_manual_pick_recipes" in prebuild.split("if manual_popover.open", 1)[1]


def test_meal_builder_defers_ingredient_index_until_needed() -> None:
    """Issue #391: Notion recipe load must not build the full ingredient index up front."""
    flow_source = (UI_ROOT / "views" / "weekly_plan" / "flow.py").read_text(encoding="utf-8")
    load_fn = flow_source.split("def _load_weekly_plan_recipes", 1)[1].split("\n\n", 1)[0]
    assert "cached_query_recipes" in load_fn
    assert "warm_weekly_plan_meal_caches" not in flow_source
    assert "_cached_plan_ingredient_index" not in load_fn
    assert "_prefetch_weekly_plan_recipes" not in flow_source

    plan_entry = (UI_ROOT / "views" / "weekly_plan" / "plan_entry.py").read_text(encoding="utf-8")
    meals_section = plan_entry.split("def render_meals_section", 1)[1].split("\ndef ", 1)[0]
    assert "_cached_plan_ingredient_index(all_recipes)" not in meals_section
    assert "_ingredient_index_for_filters" in meals_section
    assert "Loading your meals" not in meals_section
    filtered_picker = plan_entry.split("def _render_filtered_recipe_picker", 1)[1].split(
        "\ndef ", 1
    )[0]
    assert "_cached_plan_ingredient_index(all_recipes)" in filtered_picker


def test_get_started_does_not_prefetch_recipes() -> None:
    flow_source = (UI_ROOT / "views" / "weekly_plan" / "flow.py").read_text(encoding="utf-8")
    get_started_path = flow_source.split("if not weekly_plan_has_started():", 1)[1].split(
        "render_weekly_step_rail", 1
    )[0]
    assert "_warm_weekly_plan_recipes_quiet" not in get_started_path
    assert "loading_indicator" not in get_started_path


def test_long_actions_show_spinners() -> None:
    source = ui_source()
    assert "Building your meal plan" in source
    assert "Preparing ingredient review" in source
    assert "Building grocery list" in source
    refresh_fn = source.split("def _refresh_notion_cache_from_ui", 1)[1].split(
        "def _render_notion_cache_controls", 1
    )[0]
    assert "Refreshing from Notion" in refresh_fn
