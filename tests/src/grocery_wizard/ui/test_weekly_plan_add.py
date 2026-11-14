"""Browse → weekly plan add helper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.grocery_wizard.config import load_config
from src.grocery_wizard.ui.views.weekly_plan import state as weekly_state
from src.grocery_wizard.ui.weekly_plan_add import (
    WeeklyPlanAddOutcome,
    add_recipe_to_week_from_browse,
    ensure_weekly_plan_session_for_browse,
    try_append_to_built_plan,
    try_pin_recipe,
)


class _FakeSession(dict):
    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: object) -> None:
        self[key] = value


@pytest.fixture
def fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> _FakeSession:
    session = _FakeSession()
    stub = SimpleNamespace(session_state=session)
    monkeypatch.setattr(weekly_state, "st", stub, raising=False)
    return session


def test_try_pin_recipe_adds_name(fake_streamlit: _FakeSession) -> None:
    result = try_pin_recipe(fake_streamlit, "Soup", max_pins=5)
    assert result.outcome == WeeklyPlanAddOutcome.PINNED
    assert fake_streamlit["plan_prebuild_pinned_recipes"] == ["Soup"]


def test_add_starts_new_weekly_session_when_mode_unset(
    fake_streamlit: _FakeSession,
) -> None:
    result = add_recipe_to_week_from_browse(fake_streamlit, "Tomato Soup")
    assert fake_streamlit["weekly_plan_mode"] == "new"
    assert result.outcome == WeeklyPlanAddOutcome.PINNED
    assert fake_streamlit["plan_prebuild_pinned_recipes"] == ["Tomato Soup"]


def test_add_append_when_plan_has_room(fake_streamlit: _FakeSession) -> None:
    fake_streamlit.update(
        {
            "weekly_plan_mode": "new",
            "plan_meals_text": "Salad",
            "plan_meal_count": load_config().default_meals,
            "plan_slot_origins": ["manual"],
        },
    )
    result = add_recipe_to_week_from_browse(fake_streamlit, "Tacos")
    assert result.outcome == WeeklyPlanAddOutcome.ADDED
    assert fake_streamlit["plan_meals_text"] == "Salad\nTacos"
    assert fake_streamlit["plan_slot_origins"] == ["manual", "manual"]


def test_try_append_plan_full_without_replace(fake_streamlit: _FakeSession) -> None:
    default_meals = load_config().default_meals
    names = [f"Meal {index}" for index in range(default_meals)]
    fake_streamlit.update(
        {
            "plan_meals_text": "\n".join(names),
            "plan_meal_count": default_meals,
            "plan_slot_origins": ["suggested"] * default_meals,
        },
    )
    result = try_append_to_built_plan(fake_streamlit, "Extra", meal_count=default_meals)
    assert result.outcome == WeeklyPlanAddOutcome.PLAN_FULL
    assert fake_streamlit["plan_meals_text"] == "\n".join(names)


def test_ensure_weekly_plan_does_not_reset_existing_mode(
    fake_streamlit: _FakeSession,
) -> None:
    fake_streamlit["weekly_plan_mode"] = "dev"
    ensure_weekly_plan_session_for_browse(fake_streamlit)
    assert fake_streamlit["weekly_plan_mode"] == "dev"
