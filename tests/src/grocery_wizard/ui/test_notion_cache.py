"""Regression tests for Notion cache invalidation (issue #320)."""

from __future__ import annotations

from datetime import date

from ui_source import UI_ROOT

from src.grocery_wizard.planning.saved_weekly_plans import SavedWeeklyPlan
from src.grocery_wizard.ui.notion_cache import saved_plan_for_week, saved_plan_recipe_names

_NOTION_CACHE_PATH = UI_ROOT / "notion_cache.py"


def test_invalidate_notion_cache_clears_cached_db_resource() -> None:
    source = _NOTION_CACHE_PATH.read_text(encoding="utf-8")
    invalidate_block = source.split("def invalidate_notion_cache()", 1)[1].split("\n\n", 1)[0]
    assert "get_db.clear()" in invalidate_block


def _plan(week: date, name: str, *recipes: str) -> SavedWeeklyPlan:
    return SavedWeeklyPlan(week_start=week, name=name, recipes=tuple(recipes))


def test_saved_plan_for_week_reads_from_cached_list() -> None:
    plans = [_plan(date(2026, 10, 18), "A", "Soup"), _plan(date(2026, 10, 11), "B", "Pie")]
    assert saved_plan_for_week(plans, date(2026, 10, 11)) == plans[1]
    assert saved_plan_for_week(plans, date(2026, 10, 25)) is None


def test_saved_plan_recipe_names_returns_none_when_plan_missing() -> None:
    plans = [_plan(date(2026, 10, 18), "A", "Soup", "Pie")]
    assert saved_plan_recipe_names(plans, "A") == ["Soup", "Pie"]
    assert saved_plan_recipe_names(plans, "missing") is None


def test_meals_step_render_path_does_not_query_notion_directly() -> None:
    """Perf guard (#407): the save-replace check and plan load use the cached plan list."""
    state_source = (UI_ROOT / "views" / "weekly_plan" / "state.py").read_text(encoding="utf-8")
    would_replace = state_source.split("def _weekly_plan_save_would_replace", 1)[1].split(
        "\ndef ", 1
    )[0]
    assert "find_plan_for_week" not in would_replace
    assert "cached_saved_plans" in would_replace


def test_manual_pick_popovers_only_render_body_when_open() -> None:
    """Perf guard (#408): closed popovers must not build 300-option selectboxes."""
    source = (UI_ROOT / "views" / "weekly_plan" / "plan_entry.py").read_text(encoding="utf-8")
    for fn in ("_render_slot_manual_popover", "_render_plan_builder_popover"):
        body = source.split(f"def {fn}", 1)[1].split("\ndef ", 1)[0]
        assert 'on_change="rerun"' in body
        assert ".open" in body


def test_pantry_write_helpers_do_not_clear_recipe_caches() -> None:
    """Perf guard (#409): pantry and recurring writes only invalidate household reads."""
    source = (UI_ROOT / "views" / "pantry_recurring.py").read_text(encoding="utf-8")
    assert "invalidate_notion_cache" not in source
    assert "invalidate_household_cache()" in source
    cache_source = _NOTION_CACHE_PATH.read_text(encoding="utf-8")
    block = cache_source.split("def invalidate_household_cache()", 1)[1].split("\n\n\n", 1)[0]
    assert "get_db.clear()" not in block
    assert "st.cache_data.clear()" not in block
