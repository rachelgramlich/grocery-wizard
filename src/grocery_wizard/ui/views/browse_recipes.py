"""Browse recipes — image grid with meal-plan filters."""

from __future__ import annotations

import hashlib

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.planning.meal_planner import build_ingredient_index
from src.grocery_wizard.recipes.recipe_meal_plan_stats import meal_plan_status_column_name
from src.grocery_wizard.ui.browse_logic import (
    BROWSE_FILTER_KEY_PREFIX,
    BROWSE_PAGE_SIZE,
    BrowseAppliedFilters,
    applied_from_dict,
    applied_to_dict,
    browse_recipe_can_add,
    browse_recipes_for_applied,
    browse_session_add_confirmation_key,
    browse_session_applied_key,
    browse_session_sort_seed_key,
    browse_session_visible_count_key,
    clear_browse_widget_session_state,
    default_browse_applied,
    empty_browse_applied,
    new_browse_sort_seed,
    render_browse_card_box_html,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.ids import (
    CONTROL_BROWSE_APPLY,
    CONTROL_BROWSE_CARD_ADD,
    CONTROL_BROWSE_FILTERS_HAS_IMAGE,
    CONTROL_BROWSE_FILTERS_INCLUDE_DEPRECATED,
    CONTROL_BROWSE_FILTERS_INCLUDE_PAUSED,
    CONTROL_BROWSE_LOAD_MORE,
    CONTROL_BROWSE_RESET,
    control_streamlit_key,
)
from src.grocery_wizard.ui.ingredient_index_warm import (
    recipes_ingredient_cache_key,
    schedule_ingredient_index_warm,
    warmed_ingredient_index_if_ready,
)
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.meal_plan_filters import render_meal_plan_filters
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, notion_cache_generation
from src.grocery_wizard.ui.weekly_plan_add import (
    WeeklyPlanAddOutcome,
    add_recipe_to_week_from_browse,
)

_BROWSE_GRID_COLUMNS = 4
_BROWSE_RECIPES_WARM_KEY = "_browse_recipes_warm_generation"
_WEEKLY_RECIPES_WARM_KEY = "_weekly_plan_recipes_warm_generation"
_BROWSE_LOADING_MESSAGE = "Loading recipes from Notion…"


def _recipes_warm_for_session() -> bool:
    """True after recipes were loaded this session (weekly or browse tab)."""
    generation = notion_cache_generation()
    return (
        st.session_state.get(_BROWSE_RECIPES_WARM_KEY) == generation
        or st.session_state.get(_WEEKLY_RECIPES_WARM_KEY) == generation
    )


def _mark_browse_recipes_warm() -> None:
    st.session_state[_BROWSE_RECIPES_WARM_KEY] = notion_cache_generation()


def _load_browse_recipe_library(
    db: NotionRecipesDB,
) -> tuple[list[Recipe], dict[str, set[str]] | None]:
    all_recipes = cached_query_recipes(db)
    _mark_browse_recipes_warm()
    return all_recipes, _ingredient_index(all_recipes)


def _ingredient_index(recipes: list[Recipe]) -> dict[str, set[str]] | None:
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


def _browse_card_button_key(page_id: str) -> str:
    digest = hashlib.sha256(page_id.encode("utf-8")).hexdigest()[:16]
    return control_streamlit_key(f"{CONTROL_BROWSE_CARD_ADD}.{digest}")


def _render_browse_grid(
    display_recipes: list,
    *,
    limit: int,
    status_column: str | None,
) -> None:
    visible = display_recipes[:limit]
    if not visible:
        st.markdown(
            '<p class="gw-browse-empty">No recipes match these filters.</p>',
            unsafe_allow_html=True,
        )
        return

    schema = get_db().schema
    for row_start in range(0, len(visible), _BROWSE_GRID_COLUMNS):
        columns = st.columns(_BROWSE_GRID_COLUMNS, gap="small")
        for column_index, column in enumerate(columns):
            recipe_index = row_start + column_index
            if recipe_index >= len(visible):
                break
            recipe = visible[recipe_index]
            name = recipe.name or "Untitled"
            with column:
                st.markdown(
                    render_browse_card_box_html(recipe, schema=schema),
                    unsafe_allow_html=True,
                )
                can_add, disabled_help = browse_recipe_can_add(recipe, status_column=status_column)
                button_label = f"Add {name} to this week"
                if column.button(
                    button_label,
                    key=_browse_card_button_key(recipe.page_id),
                    type="secondary",
                    disabled=not can_add,
                    help=disabled_help or None,
                    use_container_width=True,
                ):
                    result = add_recipe_to_week_from_browse(st.session_state, name)
                    confirm_key = browse_session_add_confirmation_key()
                    if result.outcome in (
                        WeeklyPlanAddOutcome.PINNED,
                        WeeklyPlanAddOutcome.ADDED,
                    ):
                        st.session_state[confirm_key] = result.message
                        st.toast(result.message, icon="🍽️")
                        st.rerun()
                    else:
                        st.session_state.pop(confirm_key, None)
                        if result.message:
                            st.warning(result.message)


def render_browse_recipes() -> None:
    """Render the Browse recipes page (filters + grid)."""
    st.markdown("### Browse recipes")

    db = get_db()
    _ensure_first_visit_applied(db.schema.all_columns)
    if _recipes_warm_for_session():
        all_recipes, ingredient_index = _load_browse_recipe_library(db)
    else:
        with loading_indicator(_BROWSE_LOADING_MESSAGE):
            all_recipes, ingredient_index = _load_browse_recipe_library(db)

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
            help="When checked, only recipes whose photo can display in the grid appear.",
        )
        status_col1, status_col2 = st.columns(2)
        include_paused_draft = status_col1.checkbox(
            "Include Paused",
            value=applied.include_paused,
            key=control_streamlit_key(CONTROL_BROWSE_FILTERS_INCLUDE_PAUSED),
            help="Show recipes marked Paused in meal-plan status.",
        )
        include_deprecated_draft = status_col2.checkbox(
            "Include Deprecated",
            value=applied.include_deprecated,
            key=control_streamlit_key(CONTROL_BROWSE_FILTERS_INCLUDE_DEPRECATED),
            help="Show Deprecated recipes (they cannot be added to your week).",
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
            BrowseAppliedFilters(
                meal_filters=draft_filters,
                has_image=has_image_draft,
                include_paused=include_paused_draft,
                include_deprecated=include_deprecated_draft,
            )
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

    confirm_message = st.session_state.get(browse_session_add_confirmation_key())
    if confirm_message:
        st.success(confirm_message)

    status_column = meal_plan_status_column_name(db)
    with st.container(key="browse_grid"):
        _render_browse_grid(display_recipes, limit=visible_limit, status_column=status_column)

    if visible_limit < total and st.button(
        "Load more",
        key=control_streamlit_key(CONTROL_BROWSE_LOAD_MORE),
        type="secondary",
    ):
        st.session_state[browse_session_visible_count_key()] = visible_limit + BROWSE_PAGE_SIZE
        st.rerun()
