"""Streamlit UI for Grocery Wizard."""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit executes this file as a script; add repo root so `src.*` imports work.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.feedback import render_feedback_controls
from src.grocery_wizard.ui.notion_cache import (
    invalidate_notion_cache,
    last_recipe_cache_load_seconds,
)
from src.grocery_wizard.ui.sections.add_recipe import render_add_recipe
from src.grocery_wizard.ui.sections.pantry_recurring import render_pantry_and_recurring
from src.grocery_wizard.ui.sections.recipe_maintenance import render_recipe_maintenance
from src.grocery_wizard.ui.sections.weekly_plan import render_create_weekly_plan
from src.grocery_wizard.ui.styles import inject_app_styles
from src.grocery_wizard.ui.tabs import (
    _TAB_ADD,
    _TAB_CONTAINER_KEYS,
    _TAB_MAINTENANCE,
    _TAB_PANTRY,
    _TAB_WEEKLY,
    _UI_TABS,
)

_GW_RENDER_SECTION = "gw_render_section"
_SKIP_PICKER_RENDER_SYNC = "gw_skip_picker_render_sync"

# Re-export for tests and AppTest entry points that import from app.
__all__ = [
    "get_db",
    "main",
    "render_add_recipe",
    "render_create_weekly_plan",
    "render_pantry_and_recurring",
    "render_recipe_maintenance",
]


def _notion_load_caption() -> str:
    load_seconds = last_recipe_cache_load_seconds()
    if load_seconds is None:
        return "Recipes load from Notion on first use."
    return f"Last full recipe load: {load_seconds:.2f}s"


def _init_section_navigation_state() -> None:
    if "gw_active_tab" not in st.session_state:
        st.session_state["gw_active_tab"] = _TAB_WEEKLY
    if _GW_RENDER_SECTION not in st.session_state:
        st.session_state[_GW_RENDER_SECTION] = st.session_state["gw_active_tab"]


def _on_active_tab_change() -> None:
    st.session_state[_GW_RENDER_SECTION] = st.session_state["gw_active_tab"]


def _sync_render_section_from_picker() -> None:
    """Keep body section aligned when the picker changes without on_change."""
    if st.session_state.get(_SKIP_PICKER_RENDER_SYNC):
        st.session_state[_SKIP_PICKER_RENDER_SYNC] = False
        return
    picker_tab = st.session_state.get("gw_active_tab")
    if picker_tab and picker_tab != st.session_state.get(_GW_RENDER_SECTION):
        st.session_state[_GW_RENDER_SECTION] = picker_tab


def _refresh_notion_cache_from_ui() -> None:
    """Invalidate Notion caches; Streamlit reruns after the button callback."""
    st.session_state[_SKIP_PICKER_RENDER_SYNC] = True
    with st.spinner("Refreshing from Notion…"):
        invalidate_notion_cache()
    # Keep picker state aligned with the section we are actually rendering.
    st.session_state["gw_active_tab"] = st.session_state[_GW_RENDER_SECTION]


def _render_notion_cache_controls() -> None:
    _, refresh_col = st.columns([2, 1])
    with refresh_col:
        st.button(
            "Refresh from Notion",
            key="notion_cache_refresh",
            type="secondary",
            use_container_width=True,
            help="Reload recipes, pantry, and saved plans from Notion",
            on_click=_refresh_notion_cache_from_ui,
        )
        st.caption(_notion_load_caption())


def main() -> None:
    st.set_page_config(
        page_title="Grocery Wizard",
        page_icon="🛒",
        layout="centered",
    )
    inject_app_styles()
    st.title("Grocery Wizard")

    _init_section_navigation_state()

    _render_notion_cache_controls()
    render_feedback_controls(surface=st.session_state.get(_GW_RENDER_SECTION))

    st.segmented_control(
        "Section",
        _UI_TABS,
        key="gw_active_tab",
        label_visibility="collapsed",
        persist_state="session",
        on_change=_on_active_tab_change,
    )
    _sync_render_section_from_picker()

    active_tab = st.session_state[_GW_RENDER_SECTION]
    section_key = _TAB_CONTAINER_KEYS.get(active_tab, "unknown")

    with st.container(key=f"gw_section_{section_key}"):
        if active_tab == _TAB_WEEKLY:
            render_create_weekly_plan()
        elif active_tab == _TAB_ADD:
            render_add_recipe()
        elif active_tab == _TAB_PANTRY:
            render_pantry_and_recurring()
        elif active_tab == _TAB_MAINTENANCE:
            render_recipe_maintenance()


if __name__ == "__main__":
    main()
