"""Holistic headless smoke: app load and every primary page (CI-safe, mocked Notion).

Run the full suite with ``just smoke-ui``. Optional live Notion cases are marked separately.
"""

from __future__ import annotations

import importlib.util
from datetime import date

import pytest
from ui_source import (
    APP_PATH,
    apptest_assert_no_exception,
    apptest_open_page,
    apptest_start_app,
)

from src.grocery_wizard.planning.saved_weekly_plans import SavedWeeklyPlan
from src.grocery_wizard.ui import notion_cache
from src.grocery_wizard.ui.views import (
    PAGE_LABEL_ADD,
    PAGE_LABEL_MAINTENANCE,
    PAGE_LABEL_PANTRY,
    PAGE_LABEL_WEEKLY,
)
from tests.notion_test_env import live_notion_smoke_enabled

pytestmark = pytest.mark.holistic_ui_smoke

_LOAD_SAVED_PLANS_UNCACHED = notion_cache._load_saved_plans_cached.__wrapped__


def test_app_py_imports_without_module_level_error() -> None:
    """Streamlit Cloud loads ``app.py`` as the main module — no ImportError at import time."""
    spec = importlib.util.spec_from_file_location("gw_app_smoke_import", APP_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)


def test_holistic_first_run_renders_global_shell() -> None:
    """Equivalent to cold open: title row, refresh, feedback, weekly plan entry gate."""
    at = apptest_start_app(timeout=120)

    labels = {button.label for button in at.button}
    assert "Refresh from Notion" in labels
    assert "Submit feedback" in labels
    assert at.segmented_control[0].value == PAGE_LABEL_WEEKLY

    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan entry Continue button missing"
    radios = [r for r in at.radio if r.label == "Weekly plan session"]
    assert radios, "Weekly plan session radio missing"


@pytest.mark.parametrize(
    ("page_label", "body_needle"),
    [
        (PAGE_LABEL_PANTRY, "### Pantry"),
        (PAGE_LABEL_ADD, "Recipe URL"),
        (PAGE_LABEL_MAINTENANCE, "### Meal plan status"),
    ],
)
def test_holistic_primary_page_opens(page_label: str, body_needle: str) -> None:
    at = apptest_start_app(timeout=120)
    apptest_open_page(at, page_label, timeout=120)
    apptest_assert_no_exception(at, context=f"page {page_label!r}")

    markdown_blob = " ".join(m.value or "" for m in at.markdown)
    assert body_needle in markdown_blob


def test_holistic_weekly_entry_loads_saved_plans_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression (#417): ``cached_saved_plans`` / ``list_saved_plans`` on first weekly render."""
    from streamlit.testing.v1 import AppTest

    class _FakePlansDB:
        def __init__(self, *, recipes_db=None) -> None:
            self._recipes_db = recipes_db

        def list_plans(self, *, recipe_names_by_page_id=None) -> list[SavedWeeklyPlan]:
            assert recipe_names_by_page_id is not None
            return [
                SavedWeeklyPlan(
                    week_start=date(2026, 10, 11),
                    name="2026-10-11_plan",
                    recipes=("Soup",),
                    page_id="plan-1",
                ),
            ]

    monkeypatch.setattr(
        "src.grocery_wizard.integrations.notion_household.NotionWeeklyPlansDB",
        _FakePlansDB,
    )
    monkeypatch.setattr(notion_cache, "_load_saved_plans_cached", _LOAD_SAVED_PLANS_UNCACHED)

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)
    apptest_assert_no_exception(at, context="weekly saved plans load")
    radios = [r for r in at.radio if r.label == "Weekly plan session"]
    assert radios, "Weekly plan session radio missing"


def test_holistic_continue_saved_plan_reaches_meals_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """Saved-plan mode → Continue loads recipes into session (no Notion writes)."""
    from streamlit.testing.v1 import AppTest

    plan = SavedWeeklyPlan(
        week_start=date(2026, 10, 11),
        name="2026-10-11_plan",
        recipes=("Soup", "Salad"),
        page_id="plan-1",
    )

    class _FakePlansDB:
        def __init__(self, *, recipes_db=None) -> None:
            del recipes_db

        def list_plans(self, *, recipe_names_by_page_id=None) -> list[SavedWeeklyPlan]:
            assert recipe_names_by_page_id is not None
            return [plan]

    monkeypatch.setattr(
        "src.grocery_wizard.integrations.notion_household.NotionWeeklyPlansDB",
        _FakePlansDB,
    )
    monkeypatch.setattr(notion_cache, "_load_saved_plans_cached", _LOAD_SAVED_PLANS_UNCACHED)

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)

    session_radio = [r for r in at.radio if r.label == "Weekly plan session"]
    assert session_radio
    saved_opt = next(o for o in session_radio[0].options if "Continue a saved weekly plan" in o)
    session_radio[0].set_value(saved_opt).run(timeout=120)

    continue_buttons = [b for b in at.button if b.label == "Continue"]
    continue_buttons[0].click().run(timeout=120)
    apptest_assert_no_exception(at, context="continue saved plan")

    assert at.session_state["weekly_plan_mode"] == "saved"
    assert "Soup" in at.session_state["plan_meals_text"]
    assert at.session_state["plan_meal_count"] == 2


@pytest.mark.skipif(
    not live_notion_smoke_enabled(),
    reason="Optional live Notion: set real NOTION_API_KEY (not pytest placeholder)",
)
def test_holistic_live_saved_plan_list_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live Notion: weekly entry still renders after real saved-plan fetch (read-only)."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(notion_cache, "_load_saved_plans_cached", _LOAD_SAVED_PLANS_UNCACHED)

    at = AppTest.from_file(str(APP_PATH), default_timeout=180)
    at.run(timeout=180)
    apptest_assert_no_exception(at, context="live saved plans")
    radios = [r for r in at.radio if r.label == "Weekly plan session"]
    assert radios


@pytest.mark.skipif(
    not live_notion_smoke_enabled(),
    reason="Optional live Notion: continue saved plan through meal-count gate (read-only)",
)
def test_holistic_live_continue_saved_plan_meals_step_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(notion_cache, "_load_saved_plans_cached", _LOAD_SAVED_PLANS_UNCACHED)

    at = AppTest.from_file(str(APP_PATH), default_timeout=180)
    at.run(timeout=180)
    session_radio = [r for r in at.radio if r.label == "Weekly plan session"]
    if not session_radio:
        pytest.skip("Weekly plan session radio missing")
    saved_opt = next(
        (o for o in session_radio[0].options if "Continue a saved weekly plan" in o),
        None,
    )
    if saved_opt is None:
        pytest.skip("Saved plan mode unavailable")
    session_radio[0].set_value(saved_opt).run(timeout=180)
    if any(s.value and "No saved weekly plans" in s.value for s in at.warning):
        pytest.skip("No saved weekly plans in Notion workspace")
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Continue missing on saved plan entry"
    continue_buttons[0].click().run(timeout=180)
    apptest_assert_no_exception(at, context="live continue saved plan")
    if at.session_state["weekly_plan_mode"] == "saved":
        meal_continue = [b for b in at.button if b.label == "Continue"]
        if meal_continue:
            meal_continue[0].click().run(timeout=180)
            apptest_assert_no_exception(at, context="live meals step")
        if not at.session_state["plan_meals_text"].strip():
            pytest.skip("Selected saved plan had no recipes in Notion")
