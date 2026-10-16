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
    "st-key-meal_slot_desktop_",
    "st-key-meal_slot_mobile_",
    "gw-meal-slot-layout--mobile",
    "p.gw-meal-slot-row-anchor",
    "@media (max-width: 768px)",
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
    assert 'key=f"meal_slot_{layout}_{index}"' in plan_entry
    assert 'layout in ("desktop", "mobile")' in plan_entry
    assert "_render_meal_slot_row" in plan_entry
    assert "gw-meal-slot-row-anchor" in plan_entry
