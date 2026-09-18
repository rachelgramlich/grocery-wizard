"""Tests for weekly plan session-state helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.ui.sections.weekly_plan import state as weekly_plan_state


class _FakeSessionState:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def pop(self, key: str, default: object = None) -> object:
        return self._data.pop(key, default)

    def keys(self) -> object:
        return self._data.keys()

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
    monkeypatch.setattr(weekly_plan_state, "st", mock_st)
    return session


def test_current_plan_names_preserves_commas_in_recipe_titles(
    fake_streamlit_session: _FakeSessionState,
) -> None:
    title = "Sheet-Pan Baked Feta With Broccolini, Tomatoes and Lemon"
    weekly_plan_state._write_plan_names([title])
    assert weekly_plan_state._current_plan_names() == [title]


def test_invalidate_stale_grocery_result_clears_review_when_plan_changes(
    fake_streamlit_session: _FakeSessionState,
) -> None:
    fake_streamlit_session.grocery_per_recipe_review = {"Soup": "1 cup broth"}
    fake_streamlit_session.grocery_review_plan_fingerprint = ("soup",)
    fake_streamlit_session.plan_meals_text = "Salad"
    weekly_plan_state._invalidate_stale_grocery_result()
    assert fake_streamlit_session.get("grocery_per_recipe_review") is None


def test_invalidate_stale_grocery_result_clears_when_notion_cache_generation_changes(
    fake_streamlit_session: _FakeSessionState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.grocery_wizard.ui.grocery_flow import GROCERY_STASH_NOTION_GENERATION_KEY

    fake_streamlit_session.grocery_result = {"week_plan": ("Soup",), "items": ["flour"]}
    fake_streamlit_session.plan_meals_text = "Soup"
    setattr(fake_streamlit_session, GROCERY_STASH_NOTION_GENERATION_KEY, 1)
    monkeypatch.setattr(weekly_plan_state, "notion_cache_generation", lambda: 2)
    weekly_plan_state._invalidate_stale_grocery_result()
    assert fake_streamlit_session.get("grocery_result") is None
