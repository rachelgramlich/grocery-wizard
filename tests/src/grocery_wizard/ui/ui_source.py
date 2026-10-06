"""Concatenated Streamlit UI sources for regression string checks."""

from __future__ import annotations

from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[4] / "src" / "grocery_wizard" / "ui"
APP_PATH = UI_ROOT / "app.py"

_UI_MODULE_PATHS = (
    "app.py",
    "ids.py",
    "pages/__init__.py",
    "pages/weekly_plan/state.py",
    "pages/weekly_plan/plan_entry.py",
    "pages/weekly_plan/recipe_review.py",
    "pages/weekly_plan/flow.py",
    "pages/weekly_plan/grocery_list_ui.py",
    "pages/add_recipe.py",
    "pages/pantry_recurring.py",
    "pages/recipe_maintenance.py",
    "grocery_helpers.py",
    "grocery_flow.py",
    "meal_plan_filters.py",
    "meal_plan_status_ui.py",
)


def ui_source() -> str:
    chunks = [(UI_ROOT / rel).read_text(encoding="utf-8") for rel in _UI_MODULE_PATHS]
    return "\n\n".join(chunks)


def pantry_page_source() -> str:
    return (UI_ROOT / "pages" / "pantry_recurring.py").read_text(encoding="utf-8")


# Back-compat alias for older tests and docs during transition.
def pantry_tab_source() -> str:
    return pantry_page_source()
