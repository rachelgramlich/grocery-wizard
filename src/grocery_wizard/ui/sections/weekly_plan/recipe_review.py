"""Per-recipe ingredient review before building the grocery list."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.grocery_flow import (
    GroceryPreBuildOptions,
    build_grocery_result_payload,
    ingredient_overrides_from_review,
    persist_reviewed_ingredients_to_notion,
    review_ingredient_widget_key,
    stash_recipe_review,
    sync_recipe_review_overrides_to_session,
)
from src.grocery_wizard.ui.grocery_helpers import parse_line_items_text
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, invalidate_notion_cache
from src.grocery_wizard.ui.sections.weekly_plan.state import (
    _clear_grocery_pre_extra_items,
    _clear_grocery_result,
    _session_pantry_extra,
)


def _start_recipe_review(
    selected: list[str],
    recipes: list[Recipe],
    *,
    exclude_pantry: bool,
    recurring_text: str,
    default_recurring: list[str],
    extra_items_text: str,
) -> None:
    options = GroceryPreBuildOptions(
        exclude_pantry=exclude_pantry,
        recurring_text=recurring_text,
        default_recurring=list(default_recurring),
        extra_items_text=extra_items_text,
    )
    stash_recipe_review(st.session_state, selected, recipes, options)


def _finalize_grocery_build(
    db: NotionRecipesDB,
    selected: list[str],
    *,
    opts: dict,
    review_overrides: dict[str, str],
    save_to_notion: bool,
) -> None:
    baseline: dict[str, str] = st.session_state.get("grocery_review_baseline") or {}
    overrides = ingredient_overrides_from_review(review_overrides)
    extra_items_text = opts.get("extra_items_text", "")

    review_recipes = st.session_state.get("grocery_review_recipes")
    if review_recipes is None:
        review_recipes = cached_query_recipes(db)

    with st.spinner("Building grocery list..."):
        if save_to_notion:
            persist_reviewed_ingredients_to_notion(
                db,
                review_recipes,
                baseline=baseline,
                review=review_overrides,
            )
            invalidate_notion_cache()

        result_payload = build_grocery_result_payload(
            db,
            selected,
            exclude_pantry=opts["exclude_pantry"],
            recurring_text=opts["recurring_text"],
            extra_items_text=extra_items_text,
            pantry_extra=_session_pantry_extra(),
            ingredient_overrides=overrides,
            recipes=review_recipes,
        )

    if (
        not result_payload["items"]
        and not result_payload["excluded"]
        and not parse_line_items_text(extra_items_text)
    ):
        missing_ingredients = result_payload["missing_ingredients"]
        if missing_ingredients:
            st.warning(
                "No grocery items found — all selected recipes are missing ingredients. "
                f"Affected recipes: {', '.join(missing_ingredients)}."
            )
        else:
            st.warning("No grocery items found.")
        return

    st.session_state.grocery_result = result_payload
    st.session_state.pop("grocery_readd", None)
    st.session_state.pop("grocery_remove_once", None)
    st.session_state.pop("grocery_per_recipe_review", None)
    st.session_state.pop("grocery_review_baseline", None)
    st.session_state.pop("grocery_review_options", None)
    st.session_state.pop("grocery_review_recipes", None)
    for key in list(st.session_state.keys()):
        if key.startswith("review_ing_"):
            st.session_state.pop(key, None)
    _clear_grocery_pre_extra_items()
    st.rerun()


def _render_per_recipe_review(db: NotionRecipesDB, selected: list[str]) -> None:
    """Show one expandable text editor per recipe; build final list on confirmation."""
    review: dict[str, str] = st.session_state.grocery_per_recipe_review
    opts: dict = st.session_state.grocery_review_options

    st.markdown("### Review ingredients")
    st.caption(
        "Each recipe's ingredients are shown below. Edit or delete lines before building "
        "your grocery list."
    )

    with st.form("recipe_review_form", clear_on_submit=False):
        for idx, name in enumerate(selected):
            original_text = review.get(name, "")
            widget_key = review_ingredient_widget_key(idx)
            if widget_key not in st.session_state:
                st.session_state[widget_key] = original_text
            with st.expander(name, expanded=False):
                st.text_area(
                    "Ingredients (one per line)",
                    height=160,
                    key=widget_key,
                    label_visibility="collapsed",
                )

        save_to_notion = st.checkbox(
            "Save ingredient edits to Notion",
            help="Updates the Notion Ingredients column for recipes you changed in this step.",
        )
        submitted = st.form_submit_button("Build final list", type="primary")

    col_cancel, _ = st.columns([1, 3])
    with col_cancel:
        if st.button("Cancel", key="review_cancel"):
            _clear_grocery_result(clear_pre_extra_items=False)
            st.rerun()

    if submitted:
        review_overrides = sync_recipe_review_overrides_to_session(st.session_state, selected)
        _finalize_grocery_build(
            db,
            selected,
            opts=opts,
            review_overrides=review_overrides,
            save_to_notion=save_to_notion,
        )
