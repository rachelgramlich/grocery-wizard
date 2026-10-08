"""Weekly tab step rail, block state, and expand/collapse hooks (#328)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Literal

import streamlit as st

from src.grocery_wizard.ui.ids import (
    BLOCK_WEEKLY_GROCERY_PRE_BUILD,
    BLOCK_WEEKLY_MEALS,
    BLOCK_WEEKLY_PLAN_START,
)
from src.grocery_wizard.ui.pages.weekly_plan.state import (
    _matching_saved_plan,
    _weekly_plan_mode,
)

WEEKLY_EXPANDED_STEP_KEY = "weekly_expanded_step"

WeeklyStepState = Literal["active", "done", "upcoming"]


class WeeklyRailStep(StrEnum):
    GET_STARTED = "get_started"
    PLAN_MEALS = "plan_meals"
    GROCERY_LIST = "grocery_list"


RAIL_STEP_LABELS: dict[WeeklyRailStep, str] = {
    WeeklyRailStep.GET_STARTED: "Get started",
    WeeklyRailStep.PLAN_MEALS: "Plan meals",
    WeeklyRailStep.GROCERY_LIST: "Grocery list",
}

RAIL_STEP_ORDER: tuple[WeeklyRailStep, ...] = (
    WeeklyRailStep.GET_STARTED,
    WeeklyRailStep.PLAN_MEALS,
    WeeklyRailStep.GROCERY_LIST,
)

_BLOCK_ID_BY_STEP: dict[WeeklyRailStep, str] = {
    WeeklyRailStep.GET_STARTED: BLOCK_WEEKLY_PLAN_START,
    WeeklyRailStep.PLAN_MEALS: BLOCK_WEEKLY_MEALS,
    WeeklyRailStep.GROCERY_LIST: BLOCK_WEEKLY_GROCERY_PRE_BUILD,
}


def weekly_plan_has_started() -> bool:
    return _weekly_plan_mode() is not None


def _get_started_done() -> bool:
    return weekly_plan_has_started()


def _plan_meals_done(recipe_names: list[str]) -> bool:
    return _matching_saved_plan(recipe_names) is not None


def _grocery_list_done() -> bool:
    return bool(st.session_state.get("grocery_result"))


def _grocery_in_progress() -> bool:
    return _grocery_list_done() or st.session_state.get("grocery_per_recipe_review") is not None


def _natural_active_step(*, recipe_names: list[str]) -> WeeklyRailStep:
    if not _get_started_done():
        return WeeklyRailStep.GET_STARTED
    if not _plan_meals_done(recipe_names) and not _grocery_in_progress():
        return WeeklyRailStep.PLAN_MEALS
    if not _grocery_list_done():
        return WeeklyRailStep.GROCERY_LIST
    return WeeklyRailStep.GROCERY_LIST


def weekly_step_state(step: WeeklyRailStep, *, recipe_names: list[str]) -> WeeklyStepState:
    if step == WeeklyRailStep.GET_STARTED:
        return "done" if _get_started_done() else "active"

    if not _get_started_done():
        return "upcoming"

    active = _natural_active_step(recipe_names=recipe_names)

    if step == WeeklyRailStep.PLAN_MEALS:
        if _plan_meals_done(recipe_names):
            return "done"
        return "active" if active == step else "upcoming"

    if _grocery_list_done():
        return "done"
    if not recipe_names and not _grocery_in_progress():
        return "upcoming"
    return "active" if active == step else "upcoming"


def effective_expanded_step(*, recipe_names: list[str]) -> WeeklyRailStep:
    stored = st.session_state.get(WEEKLY_EXPANDED_STEP_KEY)
    if stored in WeeklyRailStep._value2member_map_:
        return WeeklyRailStep(stored)
    return _natural_active_step(recipe_names=recipe_names)


def set_expanded_step(step: WeeklyRailStep) -> None:
    st.session_state[WEEKLY_EXPANDED_STEP_KEY] = step.value


def clear_expanded_step_override() -> None:
    st.session_state.pop(WEEKLY_EXPANDED_STEP_KEY, None)


def _render_block_anchor(
    step: WeeklyRailStep,
    *,
    state: WeeklyStepState,
    expanded: bool,
) -> None:
    block_id = _BLOCK_ID_BY_STEP[step]
    expanded_attr = "true" if expanded else "false"
    st.markdown(
        (
            f'<p class="gw-weekly-block-anchor" '
            f'data-gw-weekly-step="{step.value}" '
            f'data-gw-block-id="{block_id}" '
            f'data-gw-weekly-state="{state}" '
            f'data-gw-weekly-expanded="{expanded_attr}" '
            f'aria-hidden="true"></p>'
        ),
        unsafe_allow_html=True,
    )


def _render_collapsed_summary(step: WeeklyRailStep) -> None:
    if step == WeeklyRailStep.GET_STARTED:
        mode = _weekly_plan_mode()
        labels = {
            "new": "New weekly plan",
            "saved": "Continue from a saved plan",
            "dev": "Dev mode (do not save)",
        }
        label = labels.get(str(mode), "Started")
        loaded = st.session_state.get("weekly_plan_loaded_name")
        if mode == "saved" and loaded:
            label = f"{label} — {loaded}"
        st.markdown(f"**Started:** {label}")
        if st.button("Change how I started", key="weekly_plan_change_mode_summary"):
            from src.grocery_wizard.ui.pages.weekly_plan.state import _reset_weekly_plan_workflow

            _reset_weekly_plan_workflow(clear_mode=True)
            st.session_state.weekly_plan_mode_choice = "new"
            clear_expanded_step_override()
            st.rerun()
        return

    if step == WeeklyRailStep.PLAN_MEALS:
        saved = st.session_state.get("weekly_plan_last_saved_name")
        if saved:
            st.caption(f"Plan saved to Notion ({saved}). Expand to edit meals.")
        else:
            st.caption("Meals in progress. Expand to edit your plan.")
        return

    if step == WeeklyRailStep.GROCERY_LIST:
        if _grocery_list_done():
            st.caption("Grocery list built. Expand to review or copy.")
        else:
            st.caption("Build your grocery list when meals are ready.")


@contextmanager
def weekly_step_block(
    step: WeeklyRailStep,
    *,
    recipe_names: list[str],
) -> Iterator[bool]:
    """Render a weekly block shell; yield True when the full body should render."""
    expanded_step = effective_expanded_step(recipe_names=recipe_names)
    state = weekly_step_state(step, recipe_names=recipe_names)
    expanded = step == expanded_step
    container_key = f"weekly_block_{step.value}"
    with st.container(key=container_key):
        _render_block_anchor(step, state=state, expanded=expanded)
        if expanded:
            yield True
        elif state == "done":
            _render_collapsed_summary(step)
            yield False
        elif state == "upcoming":
            st.caption("Complete the earlier step to unlock this section.")
            yield False
        else:
            _render_collapsed_summary(step)
            yield False


def _rail_segment_state(
    step: WeeklyRailStep,
    *,
    recipe_names: list[str],
    expanded_step: WeeklyRailStep,
) -> WeeklyStepState:
    state = weekly_step_state(step, recipe_names=recipe_names)
    if step == expanded_step and state != "upcoming":
        return "active"
    return state


def render_weekly_step_rail(*, recipe_names: list[str]) -> None:
    """Three-step progress rail; clicking a segment expands that block."""
    if not weekly_plan_has_started():
        return

    expanded_step = effective_expanded_step(recipe_names=recipe_names)
    st.markdown('<p class="gw-weekly-rail-anchor" aria-hidden="true"></p>', unsafe_allow_html=True)
    cols = st.columns(len(RAIL_STEP_ORDER))
    for col, step in zip(cols, RAIL_STEP_ORDER, strict=True):
        segment_state = _rail_segment_state(
            step, recipe_names=recipe_names, expanded_step=expanded_step
        )
        label = RAIL_STEP_LABELS[step]
        prefix = "✓ " if segment_state == "done" else ""
        with col:
            if st.button(
                f"{prefix}{label}",
                key=f"weekly_rail_{step.value}",
                use_container_width=True,
                type="primary" if segment_state == "active" else "secondary",
            ):
                set_expanded_step(step)
                st.rerun()
