"""Replace-saved-plan button writes to Notion on the same click."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import pytest

from src.grocery_wizard.planning.saved_weekly_plans import SavedWeeklyPlan, WeeklyPlanSaveResult
from src.grocery_wizard.ui.views.weekly_plan import state

WEEK = date(2026, 11, 1)
OLD = SavedWeeklyPlan(week_start=WEEK, name="2026-11-01_plan", recipes=("A", "B"), page_id="p1")
NEW_NAMES = ["A", "C"]


class _RerunError(Exception):
    """Stands in for Streamlit's rerun, which stops the script."""


class _Session(dict):
    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: object) -> None:
        self[key] = value


@pytest.fixture
def fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    session = _Session()
    reruns: list[bool] = []

    def _rerun() -> None:
        reruns.append(True)
        raise _RerunError

    fake_st = SimpleNamespace(
        session_state=session,
        button=lambda *args, **kwargs: True,
        warning=lambda *args, **kwargs: None,
        markdown=lambda *args, **kwargs: None,
        rerun=_rerun,
    )
    monkeypatch.setattr(state, "st", fake_st)
    monkeypatch.setattr(state, "loading_indicator", lambda *_a, **_k: nullcontext())
    monkeypatch.setattr(state, "_weekly_plan_mode", lambda: "saved")
    monkeypatch.setattr(state, "_resolve_save_week_start", lambda: WEEK)
    monkeypatch.setattr(state, "_save_week_choice", lambda: None)
    monkeypatch.setattr(state, "get_db", object)
    monkeypatch.setattr(state, "save_week_plan", lambda *_a, **_k: None)
    monkeypatch.setattr(state, "sync_plan_selection_stats", lambda *_a, **_k: [])
    monkeypatch.setattr(state, "invalidate_saved_plans_cache", lambda: None)
    monkeypatch.setattr(state, "_weekly_plan_save_would_replace", lambda names: (True, OLD))
    fake_st.reruns = reruns
    return fake_st


def test_replace_button_saves_to_notion_without_second_click(
    monkeypatch: pytest.MonkeyPatch, fake_streamlit: SimpleNamespace
) -> None:
    saved_calls: list[list[str]] = []

    def _ensure(names: list[str], **_kwargs: object) -> WeeklyPlanSaveResult:
        saved_calls.append(list(names))
        plan = SavedWeeklyPlan(week_start=WEEK, name=OLD.name, recipes=tuple(names), page_id="p1")
        return WeeklyPlanSaveResult(plan, "updated", OLD.recipes)

    monkeypatch.setattr(state, "ensure_saved_weekly_plan", _ensure)

    with pytest.raises(_RerunError):
        state._render_weekly_plan_overwrite_prompt(
            NEW_NAMES, OLD, confirm_button_key="weekly_plan_confirm_overwrite_save"
        )

    assert saved_calls == [NEW_NAMES]
    assert state._matching_saved_plan(NEW_NAMES) is not None
    assert fake_streamlit.reruns == [True]


def test_create_grocery_queues_prompt_instead_of_saving(
    monkeypatch: pytest.MonkeyPatch, fake_streamlit: SimpleNamespace
) -> None:
    monkeypatch.setattr(
        state,
        "ensure_saved_weekly_plan",
        lambda *_a, **_k: pytest.fail("must wait for the Replace click"),
    )

    with pytest.raises(_RerunError):
        state._ensure_weekly_plan_saved_before_grocery(NEW_NAMES)

    assert fake_streamlit.session_state[state._GROCERY_OVERWRITE_PENDING_KEY] is True
    assert fake_streamlit.reruns == [True]
