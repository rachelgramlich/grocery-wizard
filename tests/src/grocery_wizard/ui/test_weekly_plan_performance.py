"""Regression tests for weekly plan performance UX (issue #207)."""

from __future__ import annotations

from ui_source import ui_source


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


def test_ingredient_filter_uses_search_scoping() -> None:
    source = ui_source()
    assert "scoped_ingredient_multiselect_options" in source
    assert "ingredient_search" in source


def test_long_actions_show_spinners() -> None:
    source = ui_source()
    assert "Building your meal plan" in source
    assert "Preparing ingredient review" in source
    assert "Building grocery list" in source
    assert "Refreshing from Notion" in source
