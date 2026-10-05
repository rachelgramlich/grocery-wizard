"""Per-recipe ingredient review before building the grocery list."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe, recipe_lookup_key
from src.grocery_wizard.ui.grocery_flow import (
    GroceryPreBuildOptions,
    build_grocery_result_payload,
    persist_single_recipe_review_to_notion,
    recipe_review_has_unsaved_edits,
    recipe_review_save_button_key,
    recipe_review_widget_key,
    stash_recipe_review,
    sync_recipe_review_overrides_to_session,
)
from src.grocery_wizard.ui.grocery_helpers import parse_line_items_text
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, invalidate_notion_cache
from src.grocery_wizard.ui.recipe_match import (
    render_unmatched_plan_recipes_help,
    unmatched_plan_recipe_names,
)
from src.grocery_wizard.ui.sections.weekly_plan.state import (
    _clear_grocery_pre_extra_items,
    _clear_grocery_result,
    _session_pantry_extra,
    _weekly_plan_mode,
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


def _render_recipe_review_save_flash() -> None:
    flash = st.session_state.pop("grocery_review_save_flash", None)
    if flash:
        kind, message = flash
        if kind == "success":
            st.success(message)
        elif kind == "info":
            st.info(message)
        else:
            st.warning(message)


def _queue_recipe_review_save_flash(kind: str, message: str) -> None:
    st.session_state["grocery_review_save_flash"] = (kind, message)


def _save_recipe_review_to_notion(
    db: NotionRecipesDB,
    *,
    name: str,
    selected: list[str],
    review_recipes: list[Recipe],
) -> None:
    overrides = sync_recipe_review_overrides_to_session(st.session_state, selected)
    baseline = dict(st.session_state.get("grocery_review_baseline") or {})
    with loading_indicator(f"Saving **{name}** to Notion…"):
        updated = persist_single_recipe_review_to_notion(
            db,
            name=name,
            overrides=overrides,
            recipes=review_recipes,
            baseline_review=baseline,
        )
    if updated:
        invalidate_notion_cache()
        lookup = recipe_lookup_key(name)
        saved_text = overrides.get(lookup, st.session_state.get(recipe_review_widget_key(name), ""))
        baseline[name] = saved_text
        st.session_state["grocery_review_baseline"] = baseline
        _queue_recipe_review_save_flash(
            "success",
            f"Saved ingredients for **{name}** to Notion.",
        )
    else:
        _queue_recipe_review_save_flash(
            "info",
            f"No ingredient changes to save for **{name}** (already matches Notion).",
        )
    st.rerun()


def _render_per_recipe_review(db: NotionRecipesDB, selected: list[str]) -> None:
    """Show one expandable text editor per recipe; build final list on confirmation."""
    review: dict[str, str] = st.session_state.grocery_per_recipe_review
    opts: dict = st.session_state.grocery_review_options
    baseline = dict(st.session_state.get("grocery_review_baseline") or review)
    dev_mode = _weekly_plan_mode() == "dev"

    st.markdown("### Review ingredients")
    st.caption(
        "Each recipe's ingredients are listed in collapsible sections below. "
        "Open a recipe to edit lines, **Save to Notion** when ready, then use "
        "**Build final list** once every recipe looks correct."
    )
    if dev_mode:
        st.caption(
            "Dev mode: ingredient edits apply to this week's list only (Notion save disabled)."
        )

    _render_recipe_review_save_flash()

    review_recipes = st.session_state.get("grocery_review_recipes") or cached_query_recipes(db)
    render_unmatched_plan_recipes_help(
        unmatched_plan_recipe_names(selected, review_recipes),
        context="grocery",
    )

    for name in selected:
        original_text = review.get(name, "")
        widget_key = recipe_review_widget_key(name)
        if widget_key not in st.session_state:
            st.session_state[widget_key] = original_text
        with st.expander(name, expanded=False):
            st.text_area(
                "Ingredients (one per line)",
                height=160,
                key=widget_key,
                label_visibility="collapsed",
            )
            if recipe_review_has_unsaved_edits(
                name,
                session_state=st.session_state,
                baseline_review=baseline,
            ):
                st.caption(
                    "Unsaved edits — save to Notion or continue; "
                    "the final list uses your text below."
                )
            else:
                st.caption("Matches last saved baseline for this recipe.")

            if not dev_mode and st.button(
                "Save to Notion",
                key=recipe_review_save_button_key(name),
                help=(
                    "Writes this recipe's ingredient lines to Notion "
                    "without building the grocery list."
                ),
            ):
                _save_recipe_review_to_notion(
                    db,
                    name=name,
                    selected=selected,
                    review_recipes=review_recipes,
                )

    unsaved_names = [
        name
        for name in selected
        if recipe_review_has_unsaved_edits(
            name,
            session_state=st.session_state,
            baseline_review=baseline,
        )
    ]
    if unsaved_names and not dev_mode:
        st.info(
            "Not yet saved to Notion: "
            + ", ".join(f"**{n}**" for n in unsaved_names)
            + ". You can still build the list; edits below will be used even if not saved."
        )

    build_final = st.button(
        "Build final list",
        type="primary",
        help=(
            "Merge ingredients into your grocery list. "
            "Use Save to Notion per recipe before building if you want Notion updated."
        ),
    )

    col_cancel, _ = st.columns([1, 3])
    with col_cancel:
        if st.button("Cancel", key="review_cancel"):
            _clear_grocery_result(clear_pre_extra_items=False)
            st.rerun()

    if not build_final:
        return

    overrides = sync_recipe_review_overrides_to_session(st.session_state, selected)
    extra_items_text = opts.get("extra_items_text", "")

    review_recipes = st.session_state.get("grocery_review_recipes")
    if review_recipes is None:
        review_recipes = cached_query_recipes(db)
    with loading_indicator("Building grocery list…"):
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
    st.session_state.pop("grocery_final_list", None)
    st.session_state.pop("grocery_final_list_fingerprint", None)
    st.session_state.pop("meals_final_list", None)
    st.session_state.pop("meals_final_list_fingerprint", None)
    st.session_state.pop("grocery_readd", None)
    st.session_state.pop("grocery_remove_once", None)
    st.session_state.pop("grocery_per_recipe_review", None)
    st.session_state.pop("grocery_review_options", None)
    st.session_state.pop("grocery_review_recipes", None)
    st.session_state.pop("grocery_review_plan_fingerprint", None)
    st.session_state.pop("grocery_review_baseline", None)
    st.session_state.pop("grocery_review_save_flash", None)
    for key in list(st.session_state.keys()):
        key_str = str(key)
        if key_str.startswith(("review_ing_", "review_save_")):
            st.session_state.pop(key, None)
    _clear_grocery_pre_extra_items()
    st.rerun()
