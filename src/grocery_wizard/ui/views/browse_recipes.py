"""Browse recipes — image grid with meal-plan filters."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.planning.meal_planner import build_ingredient_index
from src.grocery_wizard.ui.browse_logic import (
    BROWSE_FILTER_KEY_PREFIX,
    BROWSE_PAGE_SIZE,
    BrowseAppliedFilters,
    applied_from_dict,
    applied_to_dict,
    browse_recipes_for_applied,
    browse_session_applied_key,
    browse_session_sort_seed_key,
    browse_session_visible_count_key,
    clear_browse_widget_session_state,
    default_browse_applied,
    empty_browse_applied,
    new_browse_sort_seed,
    render_browse_grid_html,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.ids import (
    CONTROL_BROWSE_APPLY,
    CONTROL_BROWSE_FILTERS_HAS_IMAGE,
    CONTROL_BROWSE_LOAD_MORE,
    CONTROL_BROWSE_RESET,
    control_streamlit_key,
)
from src.grocery_wizard.ui.ingredient_index_warm import (
    recipes_ingredient_cache_key,
    schedule_ingredient_index_warm,
    warmed_ingredient_index_if_ready,
)
from src.grocery_wizard.ui.meal_plan_filters import render_meal_plan_filters
from src.grocery_wizard.ui.notion_cache import cached_query_recipes


def _ingredient_index(recipes: list) -> dict[str, set[str]] | None:
    cache_key = recipes_ingredient_cache_key(recipes)
    warmed = warmed_ingredient_index_if_ready(cache_key)
    if warmed is not None:
        return warmed
    schedule_ingredient_index_warm(recipes)
    return build_ingredient_index(recipes)


def _ensure_first_visit_applied(schema_columns: dict) -> None:
    key = browse_session_applied_key()
    if applied_from_dict(st.session_state.get(key)) is not None:
        return
    defaults = default_browse_applied(schema_columns)
    st.session_state[key] = applied_to_dict(defaults)
    st.session_state[browse_session_sort_seed_key()] = new_browse_sort_seed()
    st.session_state[browse_session_visible_count_key()] = BROWSE_PAGE_SIZE


def render_browse_recipes() -> None:
    """Render the Browse recipes page (filters + grid)."""
    st.markdown("### Browse recipes")

    db = get_db()
    _ensure_first_visit_applied(db.schema.all_columns)
    all_recipes = cached_query_recipes(db)
    ingredient_index = _ingredient_index(all_recipes)

    applied = applied_from_dict(st.session_state.get(browse_session_applied_key()))
    assert applied is not None

    schema = db.schema
    filter_columns = [*schema.filter_columns, *schema.checkbox_columns]

    with st.container(border=True):
        st.markdown(
            '<p class="gw-heading-subsection" id="browse-filters">Filters</p>',
            unsafe_allow_html=True,
        )
        draft_filters = render_meal_plan_filters(
            filter_columns,
            applied.meal_filters,
            key_prefix=BROWSE_FILTER_KEY_PREFIX,
            ingredient_index=ingredient_index,
        )
        has_image_draft = st.checkbox(
            "Has image",
            value=applied.has_image,
            key=control_streamlit_key(CONTROL_BROWSE_FILTERS_HAS_IMAGE),
            help="When checked, only recipes with a photo in the Notion Files column appear.",
        )

        apply_col, reset_col = st.columns(2)
        apply_clicked = apply_col.button(
            "Apply filters",
            type="primary",
            key=control_streamlit_key(CONTROL_BROWSE_APPLY),
            use_container_width=True,
        )
        reset_clicked = reset_col.button(
            "Reset",
            type="secondary",
            key=control_streamlit_key(CONTROL_BROWSE_RESET),
            use_container_width=True,
        )

    if apply_clicked:
        st.session_state[browse_session_applied_key()] = applied_to_dict(
            BrowseAppliedFilters(meal_filters=draft_filters, has_image=has_image_draft)
        )
        st.session_state[browse_session_sort_seed_key()] = new_browse_sort_seed()
        st.session_state[browse_session_visible_count_key()] = BROWSE_PAGE_SIZE

    if reset_clicked:
        clear_browse_widget_session_state(st.session_state)
        st.session_state[browse_session_applied_key()] = applied_to_dict(empty_browse_applied())
        st.session_state[browse_session_sort_seed_key()] = new_browse_sort_seed()
        st.session_state[browse_session_visible_count_key()] = BROWSE_PAGE_SIZE
        st.rerun()

    applied = applied_from_dict(st.session_state.get(browse_session_applied_key()))
    assert applied is not None

    sort_seed = int(st.session_state.get(browse_session_sort_seed_key(), 0))
    visible_limit = int(st.session_state.get(browse_session_visible_count_key(), BROWSE_PAGE_SIZE))

    display_recipes = browse_recipes_for_applied(
        all_recipes,
        db,
        applied,
        ingredient_index=ingredient_index,
        sort_seed=sort_seed,
    )
    total = len(display_recipes)
    showing = min(visible_limit, total)
    st.caption(f"Showing {showing} of {total} recipes")

    st.markdown(
        render_browse_grid_html(display_recipes, limit=visible_limit, schema=db.schema),
        unsafe_allow_html=True,
    )

    if visible_limit < total and st.button(
        "Load more",
        key=control_streamlit_key(CONTROL_BROWSE_LOAD_MORE),
        type="secondary",
    ):
        st.session_state[browse_session_visible_count_key()] = visible_limit + BROWSE_PAGE_SIZE
        st.rerun()
