"""Tests for weekly step rail helpers (#328)."""

from __future__ import annotations

from src.grocery_wizard.ui.pages.weekly_plan import step_ui
from src.grocery_wizard.ui.pages.weekly_plan.step_ui import WeeklyRailStep
from src.grocery_wizard.ui.theme import app_theme_css


def test_weekly_step_state_progression(monkeypatch) -> None:
    session: dict = {}
    monkeypatch.setattr(step_ui, "_weekly_plan_mode", lambda: session.get("weekly_plan_mode"))
    monkeypatch.setattr(
        step_ui,
        "_matching_saved_plan",
        lambda names: object() if session.get("saved") else None,
    )
    monkeypatch.setattr(step_ui.st, "session_state", session, raising=False)

    assert step_ui.weekly_step_state(WeeklyRailStep.GET_STARTED, recipe_names=[]) == "active"

    session["weekly_plan_mode"] = "new"
    assert step_ui.weekly_step_state(WeeklyRailStep.GET_STARTED, recipe_names=[]) == "done"
    assert step_ui.weekly_step_state(WeeklyRailStep.PLAN_MEALS, recipe_names=[]) == "active"
    assert step_ui.weekly_step_state(WeeklyRailStep.GROCERY_LIST, recipe_names=[]) == "upcoming"

    session["saved"] = True
    assert step_ui.weekly_step_state(WeeklyRailStep.PLAN_MEALS, recipe_names=["tacos"]) == "done"
    assert (
        step_ui.weekly_step_state(WeeklyRailStep.GROCERY_LIST, recipe_names=["tacos"]) == "active"
    )

    session["grocery_result"] = {"items": []}
    assert step_ui.weekly_step_state(WeeklyRailStep.GROCERY_LIST, recipe_names=["tacos"]) == "done"


def test_effective_expanded_step_honors_override(monkeypatch) -> None:
    session = {"weekly_plan_mode": "new", step_ui.WEEKLY_EXPANDED_STEP_KEY: "get_started"}
    monkeypatch.setattr(step_ui.st, "session_state", session, raising=False)
    assert step_ui.effective_expanded_step(recipe_names=[]) == WeeklyRailStep.GET_STARTED


def test_collapse_after_plan_saved_clears_rail_override(monkeypatch) -> None:
    session = {step_ui.WEEKLY_EXPANDED_STEP_KEY: "plan_meals"}
    monkeypatch.setattr(step_ui.st, "session_state", session, raising=False)
    step_ui.collapse_after_plan_saved_to_notion()
    assert step_ui.WEEKLY_EXPANDED_STEP_KEY not in session


def test_natural_active_step_after_plan_saved(monkeypatch) -> None:
    session = {"weekly_plan_mode": "new"}
    monkeypatch.setattr(step_ui, "_weekly_plan_mode", lambda: session.get("weekly_plan_mode"))
    monkeypatch.setattr(step_ui, "_matching_saved_plan", lambda names: object())
    monkeypatch.setattr(step_ui.st, "session_state", session, raising=False)
    assert step_ui._natural_active_step(recipe_names=["tacos"]) == WeeklyRailStep.GROCERY_LIST


def test_app_theme_css_includes_weekly_rail_hooks() -> None:
    css = app_theme_css()
    for fragment in (
        "gw-weekly-rail-anchor",
        "gw-weekly-block-anchor",
        "data-gw-weekly-state",
        "st-key-weekly_block_",
    ):
        assert fragment in css
