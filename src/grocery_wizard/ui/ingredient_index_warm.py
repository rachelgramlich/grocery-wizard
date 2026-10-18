"""Background warm for the meal-plan ingredient index (issue #406)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import streamlit as st

from src.grocery_wizard.planning.meal_planner import build_ingredient_index
from src.grocery_wizard.ui.meal_plan_filters import recipes_ingredient_cache_key

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import Recipe


@dataclass
class _WarmState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    cache_key: tuple[tuple[str, str], ...] | None = None
    index: dict[str, set[str]] | None = None
    in_progress: bool = False


@st.cache_resource(show_spinner=False)
def _warm_state() -> _WarmState:
    return _WarmState()


def clear_ingredient_index_warm() -> None:
    """Drop process-wide warm state (Refresh from Notion)."""
    _warm_state.clear()


def schedule_ingredient_index_warm(recipes: list[Recipe]) -> None:
    """Parse ingredients in a daemon thread; never call Streamlit from that thread."""
    cache_key = recipes_ingredient_cache_key(recipes)
    state = _warm_state()
    with state.lock:
        if state.cache_key == cache_key and state.index is not None:
            return
        if state.in_progress and state.cache_key == cache_key:
            return
        state.cache_key = cache_key
        state.index = None
        state.in_progress = True

    snapshot = list(recipes)

    def _run() -> None:
        built = build_ingredient_index(snapshot)
        with state.lock:
            if state.cache_key == cache_key:
                state.index = built
            state.in_progress = False

    threading.Thread(target=_run, daemon=True, name="gw-ingredient-index-warm").start()


def warmed_ingredient_index_if_ready(
    cache_key: tuple[tuple[str, str], ...],
) -> dict[str, set[str]] | None:
    state = _warm_state()
    with state.lock:
        if state.cache_key == cache_key and state.index is not None:
            return state.index
    return None
