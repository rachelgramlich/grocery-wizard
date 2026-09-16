"""Pre-build grocery options and final grocery list display."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.shopping.grocery_list import (
    align_item_provenance_with_items,
    format_grocery_items_copy_text,
    format_item_provenance,
    format_meals_copy_text,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.grocery_flow import default_pre_build_grocery_options
from src.grocery_wizard.ui.grocery_helpers import (
    compute_grocery_drafts,
    meal_entries_with_links,
    parse_line_items_text,
    render_copy_download,
)
from src.grocery_wizard.ui.notion_cache import cached_query_recipes
from src.grocery_wizard.ui.sections.weekly_plan.recipe_review import (
    _render_per_recipe_review,
    _start_recipe_review,
)
from src.grocery_wizard.ui.sections.weekly_plan.state import (
    _clear_grocery_result,
    _ensure_weekly_plan_saved_before_grocery,
    _grocery_pre_extra_items_widget_key,
    _save_week_choice_label,
)


def _build_result_added_items(result: dict) -> list[str]:
    recurring_items: list[str] = result.get("recurring_items") or []
    extra_items = parse_line_items_text(result.get("additional_text", ""))
    added_items: list[str] = []
    seen: set[str] = set()
    for item in [*recurring_items, *extra_items]:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        added_items.append(item)
    return added_items


def _buy_list_line_options(result: dict) -> list[str]:
    """Lines on the buy list before one-time removals (for adjust multiselects)."""
    readd: list[str] = result.get("readd") or []
    _, lines = compute_grocery_drafts(
        result["items"],
        readd,
        result.get("additional_text", ""),
        run_removals=None,
    )
    return lines


def _run_removal_defaults(result: dict, buy_lines: list[str]) -> list[str]:
    removal_keys = {name.strip().lower() for name in (result.get("run_removals") or [])}
    if not removal_keys:
        return []
    defaults: list[str] = []
    for line in buy_lines:
        lowered = line.strip().lower()
        if any(key in lowered or lowered in key for key in removal_keys):
            defaults.append(line)
    return defaults


def _render_build_result_summary(result: dict) -> None:
    added_items = _build_result_added_items(result)
    excluded: list[str] = list(result.get("excluded") or [])

    st.markdown("### Summary (build result)")
    col_added, col_removed = st.columns(2)
    with col_added:
        st.markdown("**Added: recurring items and pasted extras**")
        if added_items:
            for item in added_items:
                st.write(f"- {item}")
        else:
            st.write("_None_")
    with col_removed:
        st.markdown("**Removed: items in the pantry**")
        if excluded:
            for item in excluded:
                st.write(f"- {item}")
        else:
            st.write("_None_")


def _render_adjust_this_week_list(result: dict) -> None:
    excluded: list[str] = list(result.get("excluded") or [])
    buy_lines = _buy_list_line_options(result)

    with st.expander("Adjust this week's list", expanded=False):
        if excluded:
            readd = st.multiselect(
                "Add to grocery list from pantry (1x)",
                options=excluded,
                default=result.get("readd", []),
                key="grocery_readd",
                help="Add pantry-removed items back for this trip only.",
            )
            result["readd"] = readd
        else:
            st.caption("No pantry-removed items to add back.")
            result["readd"] = []

        if buy_lines:
            remove_once = st.multiselect(
                "Remove from grocery list (1x)",
                options=buy_lines,
                default=_run_removal_defaults(result, buy_lines),
                key="grocery_remove_once",
                help="Skip these lines on this trip only; they are not added to the pantry.",
            )
            result["run_removals"] = sorted(
                {line.strip().lower() for line in remove_once if line.strip()}
            )
        else:
            st.caption("No buy-list lines to remove for this run.")


def _render_added_and_removed_summary(result: dict) -> None:
    """Post-build summary plus week-only list adjustments."""
    _render_build_result_summary(result)
    _render_adjust_this_week_list(result)


def render_grocery_list_section(
    db: NotionRecipesDB,
    *,
    all_recipes: list[Recipe],
    current_plan: list[str],
) -> None:
    """Render step 2 (grocery list): result, review, or pre-build controls."""
    st.divider()
    st.markdown("### 2. Grocery list")

    if st.session_state.get("grocery_result"):
        _render_grocery_result()
        return

    if st.session_state.get("grocery_per_recipe_review") is not None:
        _render_per_recipe_review(db, current_plan)
        return

    if not current_plan:
        st.caption("Build a meal plan above to continue.")
        return

    pre_build_defaults = default_pre_build_grocery_options(st.session_state)
    default_recurring = pre_build_defaults.default_recurring
    exclude_pantry = pre_build_defaults.exclude_pantry
    recurring_text = pre_build_defaults.recurring_text

    with st.expander("Pantry & Recurring Items", expanded=False):
        exclude_pantry = st.checkbox("Exclude pantry items", value=True)
        st.caption(
            "Edit saved pantry staples and recurring defaults in the **Pantry & recurring** tab."
        )
        recurring_text = st.text_area(
            "Recurring items for this week (one per line)",
            value="\n".join(default_recurring),
            height=100,
            help="Edits here apply to this run only; change saved defaults in Pantry & recurring.",
        )

    with st.expander("Add extra items", expanded=False):
        st.caption(
            "One-off items for this grocery run (not saved as recurring). "
            "Enter one item per line — checklist lines like `- [ ] Flowers` are OK."
        )
        extra_items_text = st.text_area(
            "Extra items (one per line)",
            placeholder="Start typing — one item per line",
            height=80,
            key=_grocery_pre_extra_items_widget_key(),
            label_visibility="collapsed",
        )

    week_label = _save_week_choice_label()
    if week_label:
        st.caption(f"Meal plan saves to **{week_label}** (change above in your meal list).")

    if st.button("Create grocery list", type="primary", key="create_grocery"):
        _ensure_weekly_plan_saved_before_grocery(current_plan)
        _clear_grocery_result(clear_pre_extra_items=False)
        _start_recipe_review(
            current_plan,
            all_recipes,
            exclude_pantry=exclude_pantry,
            recurring_text=recurring_text,
            default_recurring=default_recurring,
            extra_items_text=extra_items_text,
        )
        st.rerun()


def _render_grocery_result() -> None:
    result = st.session_state.grocery_result
    items: list[str] = result["items"]
    excluded: list[str] = result["excluded"]
    missing_ingredients: list[str] = result.get("missing_ingredients", [])
    name_link_mismatches = result.get("name_link_mismatches", [])
    meal_names = list(result.get("week_plan") or result.get("source_recipes") or [])

    if name_link_mismatches:
        for mismatch in name_link_mismatches:
            st.warning(
                f"Name/link mismatch for **{mismatch.recipe_name}**: "
                f"Link points to **{mismatch.link_title}**. "
                "Ingredients may be stale — verify Notion Name, Link, and Ingredients match."
            )

    if missing_ingredients:
        st.warning(
            f"Skipped {len(missing_ingredients)} recipe(s) with no ingredients in Notion: "
            f"{', '.join(missing_ingredients)}. "
            "Run `dev backfill-ingredients` to populate them from their links."
        )

    _render_added_and_removed_summary(result)
    items = result["items"]
    excluded = result["excluded"]

    readd: list[str] = list(result.get("readd") or [])
    additional_text = result.get("additional_text", "")

    run_removals = set(result.get("run_removals") or [])
    _, final_items = compute_grocery_drafts(
        items,
        readd,
        additional_text,
        run_removals=run_removals,
    )

    aligned_provenance = align_item_provenance_with_items(
        result.get("item_provenance", {}),
        final_items,
    )
    if aligned_provenance:
        with st.expander("Item sources (which recipe each item came from)"):
            st.text(format_item_provenance(aligned_provenance))

    if final_items or meal_names:
        db = get_db()
        meals = meal_entries_with_links(meal_names, cached_query_recipes(db))
        meals_copy_text = format_meals_copy_text(meals)
        grocery_copy_text = format_grocery_items_copy_text(final_items)

        st.markdown("### Customize list")
        st.caption("Edit meals and grocery copy before copying.")
        st.markdown("**Meals**")
        meals_fingerprint = tuple(meals)
        if st.session_state.get("meals_final_list_fingerprint") != meals_fingerprint:
            st.session_state["meals_final_list_fingerprint"] = meals_fingerprint
            st.session_state["meals_final_list"] = meals_copy_text
        st.text_area(
            "Meals",
            height=120,
            label_visibility="collapsed",
            key="meals_final_list",
        )
        meals_for_copy = st.session_state.get("meals_final_list", meals_copy_text)
        render_copy_download(
            meals_for_copy,
            label="Download meals",
            key="meals_copy",
            file_name="meals.txt",
        )

        st.markdown("**Grocery List**")
        st.caption("Edit the list below before copying.")
        grocery_fingerprint = (tuple(final_items),)
        if st.session_state.get("grocery_final_list_fingerprint") != grocery_fingerprint:
            st.session_state["grocery_final_list_fingerprint"] = grocery_fingerprint
            st.session_state["grocery_final_list"] = grocery_copy_text
        st.text_area(
            "Grocery list",
            height=320,
            label_visibility="collapsed",
            key="grocery_final_list",
            help="Edit this consolidated list directly before copy.",
        )
        grocery_for_copy = st.session_state.get("grocery_final_list", grocery_copy_text)
        render_copy_download(
            grocery_for_copy,
            label="Download list",
            key="grocery_copy",
            file_name="grocery-list.txt",
        )
    elif not excluded and not meal_names:
        st.warning("No grocery items found.")

    edit_count: int = result.get("edit_count", 0)
    if edit_count:
        st.caption(f"_{edit_count} ingredient edit(s) logged for later review._")
