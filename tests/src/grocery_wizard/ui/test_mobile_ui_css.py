"""Mobile layout and touch-target CSS hooks (issue #378)."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT

from src.grocery_wizard.ui.theme import app_theme_css

_REQUIRED_MOBILE_CSS_FRAGMENTS = (
    "@media (max-width: 480px)",
    "--gw-touch-min-height",
    "p.gw-global-page-picker-anchor",
    "p.gw-global-header-actions",
    "p.gw-weekly-rail-anchor",
    "p.gw-meal-slot-label",
    "p.gw-pantry-item",
    "overflow-x: clip",
    "st-key-global_global_page_picker",
    "st-key-gw_global_header",
    "st-key-meal_slot_action_row",
    "st-key-meal_slot_row_",
    "p.gw-meal-slot-row-anchor",
    "@media (max-width: 768px)",
    "gw-meal-slot-row-anchor",
    "st-key-weekly_step_rail",
    "st-key-plan_week_action_row",
    '[data-testid="stMarkdownContainer"]:has(> p.gw-meal-slot-label)',
)


def test_app_theme_css_includes_mobile_pass_hooks() -> None:
    css = app_theme_css()
    missing = [frag for frag in _REQUIRED_MOBILE_CSS_FRAGMENTS if frag not in css]
    assert not missing, f"app_theme_css missing mobile hooks: {missing}"


def test_app_exposes_page_picker_css_anchor() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "gw-global-page-picker-anchor" in app
    picker_idx = app.index("st.segmented_control(")
    anchor_idx = app.index("gw-global-page-picker-anchor")
    assert anchor_idx < picker_idx


def test_meal_rows_use_stackable_container_keys() -> None:
    plan_entry = (UI_ROOT / "views" / "weekly_plan" / "plan_entry.py").read_text(encoding="utf-8")
    assert 'key=f"meal_slot_row_{index}"' in plan_entry
    assert "gw-meal-slot-row-anchor" in plan_entry


def test_meal_row_wraps_with_one_flex_rule_not_a_display_hack() -> None:
    """Meal rows wrap on their own; stacking hacks fought Streamlit's -1rem markdown margin."""
    css = app_theme_css()
    row_rule = css.split('[data-testid="stHorizontalBlock"]:has(p.gw-meal-slot-label) {', 1)[1]
    row_rule = row_rule.split("}", 1)[0]
    assert "flex-wrap: wrap !important" in row_rule
    assert "flex-direction" not in row_rule
    label_fix = css.split('[data-testid="stMarkdownContainer"]:has(> p.gw-meal-slot-label) {', 1)[1]
    assert "margin-bottom: 0 !important" in label_fix.split("}", 1)[0]
    mobile = css.split("@media (max-width: 768px)", 1)[1]
    assert "display: block" not in mobile


def test_mobile_rules_are_scoped_to_keyed_containers_not_ancestor_anchors() -> None:
    """``stVerticalBlock:has(p.anchor)`` also matches the page block and restyles every row."""
    css = app_theme_css()
    mobile = css.split("@media (max-width: 480px)", 1)[1]
    for anchor in (
        "gw-global-header-actions",
        "gw-global-page-picker-anchor",
        "gw-weekly-rail-anchor",
        "gw-plan-week-actions",
    ):
        assert f'stVerticalBlock"]:has(p.{anchor})' not in mobile, anchor
