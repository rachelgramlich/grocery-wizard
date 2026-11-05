"""Concatenated Streamlit UI sources for regression string checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.repo_paths import UI_SRC_ROOT

if TYPE_CHECKING:
    from streamlit.testing.v1 import AppTest

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


def apptest_start_app(*, timeout: int = 60) -> AppTest:
    """Load ``app.py`` headless, run it once, and fail on any exception."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=timeout)
    at.run(timeout=timeout)
    apptest_assert_no_exception(at, context="first run")
    return at


def apptest_open_page(at, page_label: str, *, timeout: int = 60) -> None:
    """Switch primary pages via the global segmented control."""
    assert at.segmented_control, "Page segmented control missing"
    at.segmented_control[0].set_value(page_label).run(timeout=timeout)


def apptest_assert_no_exception(at, *, context: str = "AppTest run") -> None:
    assert not at.exception, f"{context}: {[str(e.value) for e in at.exception]}"


def apptest_enter_dev_mode(at, *, timeout: int = 120) -> None:
    """Weekly plan → Dev mode → meal-count Continue (requires ``GROCERY_WIZARD_DEV_UI=1``)."""
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan Continue missing"
    continue_buttons[0].click().run(timeout=timeout)
    apptest_rail_get_started(at, timeout=timeout)

    change = [b for b in at.button if b.label == "Change how I started"]
    assert change, "Change how I started missing"
    change[0].click().run(timeout=timeout)

    session_radio = [r for r in at.radio if r.label == "Weekly plan session"]
    assert session_radio, "Weekly plan session radio missing"
    dev_opt = next(o for o in session_radio[0].options if "Dev mode" in o)
    session_radio[0].set_value(dev_opt).run(timeout=timeout)
    apptest_continue_to_meal_builder(at, timeout=timeout)
