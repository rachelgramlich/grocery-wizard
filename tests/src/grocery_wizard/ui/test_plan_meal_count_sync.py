"""Tests for meal-count widget syncing plan length (issue #284)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.ui.sections.weekly_plan import plan_entry, state as weekly_plan_state


class _FakeSessionState:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def pop(self, key: str, default: object = None) -> object:
        return self._data.pop(key, default)

    def __setitem__(self, key: str, value: object) -> None:
        self._data[key] = value

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_data":
            super().__setattr__(name, value)
            return
        self._data[name] = value

    def __getattr__(self, name: str) -> object:
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


@pytest.fixture
def fake_streamlit_session(monkeypatch: pytest.MonkeyPatch) -> _FakeSessionState:
    session = _FakeSessionState()
    mock_st = MagicMock()
    mock_st.session_state = session
    monkeypatch.setattr(plan_entry, "st", mock_st)
    monkeypatch.setattr(weekly_plan_state, "st", mock_st)
    return session


def test_sync_plan_length_trims_extra_meals(
    fake_streamlit_session: _FakeSessionState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit_session.plan_meals_text = "A\nB\nC"
    fake_streamlit_session.plan_prebuild_pinned_recipes = ["A", "B", "C"]
    cleared: list[str] = []

    monkeypatch.setattr(
        plan_entry, "_invalidate_weekly_plan_save_state", lambda: cleared.append("save")
    )
    monkeypatch.setattr(
        plan_entry, "_clear_grocery_session_overrides", lambda: cleared.append("overrides")
    )
    monkeypatch.setattr(plan_entry, "_clear_grocery_result", lambda: cleared.append("result"))

    plan_entry._sync_plan_length_to_meal_count(2)

    assert fake_streamlit_session.plan_meals_text == "A\nB"
    assert fake_streamlit_session.plan_prebuild_pinned_recipes == ["A", "B"]
    assert cleared == ["save", "overrides", "result"]


def test_sync_plan_length_no_op_when_plan_fits(
    fake_streamlit_session: _FakeSessionState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit_session.plan_meals_text = "A\nB"
    monkeypatch.setattr(
        plan_entry,
        "_invalidate_weekly_plan_save_state",
        lambda: pytest.fail("should not invalidate"),
    )

    plan_entry._sync_plan_length_to_meal_count(3)

    assert fake_streamlit_session.plan_meals_text == "A\nB"
