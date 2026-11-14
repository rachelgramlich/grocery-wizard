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
    "views/browse_recipes.py",
    "browse_logic.py",
    "grocery_helpers.py",
    "grocery_flow.py",
    "meal_plan_filters.py",
    "meal_plan_status_ui.py",
)


def ui_source() -> str:
    return "\n\n".join(ui_module_source(rel) for rel in _UI_MODULE_PATHS)


def ui_module_source(rel: str) -> str:
    return (UI_ROOT / rel).read_text(encoding="utf-8")


def app_source() -> str:
    return ui_module_source("app.py")


def weekly_plan_source(filename: str) -> str:
    return ui_module_source(f"views/weekly_plan/{filename}")


def meal_plan_filters_source() -> str:
    return ui_module_source("meal_plan_filters.py")


def pantry_page_source() -> str:
    return ui_module_source("views/pantry_recurring.py")


def add_recipe_page_source() -> str:
    return ui_module_source("views/add_recipe.py")


def browse_recipes_page_source() -> str:
    return ui_module_source("views/browse_recipes.py")


def grocery_helpers_source() -> str:
    return ui_module_source("grocery_helpers.py")


def loading_component_source() -> str:
    return ui_module_source("components/loading.py")


def feedback_component_source() -> str:
    return ui_module_source("components/feedback.py")


def nyt_sync_ui_source() -> str:
    return ui_module_source("nyt_sync.py")


def views_nav_source() -> str:
    return ui_module_source("views/__init__.py")


def notion_cache_source() -> str:
    return ui_module_source("notion_cache.py")


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


def apptest_from_app(*, timeout: int = 60) -> AppTest:
    """Headless ``AppTest`` bound to ``app.py`` (no run yet)."""
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(APP_PATH), default_timeout=timeout)


def apptest_start_app(*, timeout: int = 60) -> AppTest:
    """Load ``app.py`` headless, run it once, and fail on any exception."""
    at = apptest_from_app(timeout=timeout)
    at.run(timeout=timeout)
    apptest_assert_no_exception(at, context="first run")
    return at


def apptest_page_picker(at):
    from src.grocery_wizard.ui.ids import CONTROL_GLOBAL_PAGE_PICKER, control_streamlit_key

    key = control_streamlit_key(CONTROL_GLOBAL_PAGE_PICKER)
    return next(sc for sc in at.segmented_control if sc.key == key)


def apptest_open_page(at, page_label: str, *, timeout: int = 60) -> None:
    """Switch pages via the top segmented page picker."""
    apptest_page_picker(at).set_value(page_label).run(timeout=timeout)


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
