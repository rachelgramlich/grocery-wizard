"""Concatenated Streamlit UI sources for regression string checks."""

from __future__ import annotations

from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[4] / "src" / "grocery_wizard" / "ui"
APP_PATH = UI_ROOT / "app.py"

_UI_MODULE_PATHS = (
    "app.py",
    "ids.py",
    "views/__init__.py",
    "views/weekly_plan/state.py",
    "views/weekly_plan/plan_entry.py",
    "views/weekly_plan/recipe_review.py",
    "views/weekly_plan/flow.py",
    "views/weekly_plan/step_ui.py",
    "views/weekly_plan/grocery_list_ui.py",
    "views/add_recipe.py",
    "views/pantry_recurring.py",
    "views/recipe_maintenance.py",
    "grocery_helpers.py",
    "grocery_flow.py",
    "meal_plan_filters.py",
    "meal_plan_status_ui.py",
)


def ui_source() -> str:
    chunks = [(UI_ROOT / rel).read_text(encoding="utf-8") for rel in _UI_MODULE_PATHS]
    return "\n\n".join(chunks)


def pantry_page_source() -> str:
    return (UI_ROOT / "views" / "pantry_recurring.py").read_text(encoding="utf-8")


def apptest_continue_to_meal_builder(at, *, timeout: int = 60) -> None:
    """Click **Continue** on the meal-count gate (Plan meals step)."""
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Meal count Continue button missing"
    continue_buttons[0].click().run(timeout=timeout)


# Back-compat alias for older tests and docs during transition.
def pantry_tab_source() -> str:
    return pantry_page_source()
