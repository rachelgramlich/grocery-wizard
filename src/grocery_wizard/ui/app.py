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
from src.grocery_wizard.ui.ids import (
    CONTROL_GLOBAL_FEEDBACK,
    CONTROL_GLOBAL_PAGE_PICKER,
    CONTROL_GLOBAL_REFRESH,
    PAGE_SLUG_ADD,
    PAGE_SLUG_MAINTENANCE,
    PAGE_SLUG_PANTRY,
    PAGE_SLUG_WEEKLY,
    control_streamlit_key,
)
from src.grocery_wizard.ui.loading import loading_indicator, mount_global_loading_banner
from src.grocery_wizard.ui.notion_cache import (
    invalidate_notion_cache,
    last_recipe_cache_load_seconds,
)
from src.grocery_wizard.ui.pages import (
    PAGE_LABEL_WEEKLY,
    PAGE_PICKER_LABELS,
    page_label_for_slug,
    page_slug_for_label,
)
from src.grocery_wizard.ui.pages.add_recipe import render_add_recipe
from src.grocery_wizard.ui.pages.pantry_recurring import render_pantry_and_recurring
from src.grocery_wizard.ui.pages.recipe_maintenance import render_recipe_maintenance
from src.grocery_wizard.ui.pages.weekly_plan import render_create_weekly_plan
from src.grocery_wizard.ui.styles import inject_app_styles

_GW_RENDER_PAGE_SLUG = "gw_render_page_slug"
_SKIP_PICKER_RENDER_SYNC = "gw_skip_picker_render_sync"
_PAGE_PICKER_SESSION_KEY = control_streamlit_key(CONTROL_GLOBAL_PAGE_PICKER)

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


def _init_page_navigation_state() -> None:
    if _PAGE_PICKER_SESSION_KEY not in st.session_state:
        st.session_state[_PAGE_PICKER_SESSION_KEY] = PAGE_LABEL_WEEKLY
    if _GW_RENDER_PAGE_SLUG not in st.session_state:
        st.session_state[_GW_RENDER_PAGE_SLUG] = page_slug_for_label(
            st.session_state[_PAGE_PICKER_SESSION_KEY]
        )


def _on_active_page_change() -> None:
    label = st.session_state[_PAGE_PICKER_SESSION_KEY]
    st.session_state[_GW_RENDER_PAGE_SLUG] = page_slug_for_label(label)


def _sync_render_page_from_picker() -> None:
    """Keep body page aligned when the picker changes without on_change."""
    if st.session_state.get(_SKIP_PICKER_RENDER_SYNC):
        st.session_state[_SKIP_PICKER_RENDER_SYNC] = False
        return
    picker_label = st.session_state.get(_PAGE_PICKER_SESSION_KEY)
    if picker_label:
        picker_slug = page_slug_for_label(picker_label)
        if picker_slug != st.session_state.get(_GW_RENDER_PAGE_SLUG):
            st.session_state[_GW_RENDER_PAGE_SLUG] = picker_slug


def _refresh_notion_cache_from_ui() -> None:
    """Invalidate Notion caches; Streamlit reruns after the button callback."""
    st.session_state[_SKIP_PICKER_RENDER_SYNC] = True
    with loading_indicator("Refreshing from Notion…"):
        invalidate_notion_cache()
    slug = st.session_state[_GW_RENDER_PAGE_SLUG]
    label = page_label_for_slug(slug)
    if label is not None:
        st.session_state[_PAGE_PICKER_SESSION_KEY] = label


def _render_notion_cache_controls() -> None:
    _, refresh_col = st.columns([2, 1])
    with refresh_col:
        st.button(
            "Refresh from Notion",
            key=control_streamlit_key(CONTROL_GLOBAL_REFRESH),
            type="secondary",
            use_container_width=True,
            help="Reload recipes, pantry, saved plans, and database column options from Notion",
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
    mount_global_loading_banner()

    _init_page_navigation_state()

    _render_notion_cache_controls()
    render_feedback_controls(
        surface=st.session_state.get(_GW_RENDER_PAGE_SLUG),
        control_id=CONTROL_GLOBAL_FEEDBACK,
    )

    st.segmented_control(
        "Page",
        PAGE_PICKER_LABELS,
        key=_PAGE_PICKER_SESSION_KEY,
        label_visibility="collapsed",
        persist_state="session",
        on_change=_on_active_page_change,
    )
    _sync_render_page_from_picker()

    active_slug = st.session_state[_GW_RENDER_PAGE_SLUG]

    with st.container(key=f"gw_page_{active_slug}"):
        if active_slug == PAGE_SLUG_WEEKLY:
            render_create_weekly_plan()
        elif active_slug == PAGE_SLUG_ADD:
            render_add_recipe()
        elif active_slug == PAGE_SLUG_PANTRY:
            render_pantry_and_recurring()
        elif active_slug == PAGE_SLUG_MAINTENANCE:
            render_recipe_maintenance()


if __name__ == "__main__":
    main()
