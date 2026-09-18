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
