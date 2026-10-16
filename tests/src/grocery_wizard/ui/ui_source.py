"""Concatenated Streamlit UI sources for regression string checks."""

from __future__ import annotations

from tests.repo_paths import UI_SRC_ROOT

UI_ROOT = UI_SRC_ROOT
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


def apptest_rail_get_started(at, *, timeout: int = 60) -> None:
    """Expand **Get started** via the step rail (after the first Continue)."""
    rail = [b for b in at.button if b.label.endswith("Get started")]
    assert rail, "Get started rail button missing"
    rail[0].click().run(timeout=timeout)
