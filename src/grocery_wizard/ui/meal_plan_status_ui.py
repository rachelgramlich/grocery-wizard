"""Streamlit controls for Notion meal-plan status (Active / Favorite / Paused / Deprecated)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import streamlit as st

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    DEFAULT_MEAL_PLAN_STATUS_COLUMN,
    MEAL_PLAN_STATUS_OPTIONS,
    meal_plan_status,
    meal_plan_status_column_name,
)
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.notion_cache import invalidate_notion_cache


@dataclass(frozen=True)
class MealPlanStatusEditorContext:
    column_name: str
    options: tuple[str, ...]


def _configured_status_column_label(db: NotionRecipesDB) -> str:
    configured = db._config.meal_plan_status_column
    if configured and str(configured).strip():
        return str(configured).strip()
    return DEFAULT_MEAL_PLAN_STATUS_COLUMN


def meal_plan_status_unavailable_message(db: NotionRecipesDB) -> str | None:
    """Human-readable reason the editor cannot be used, or None if editing is allowed."""
    if meal_plan_status_column_name(db) is not None:
        return None
    label = _configured_status_column_label(db)
    column = db.schema.all_columns.get(label)
    if column is None:
        return (
            f"This Notion database has no **{label}** column. "
            "Add a select or status column with that name to edit meal-plan status here."
        )
    if column.type not in ("select", "status"):
        return f"**{label}** must be a Notion select or status column (found `{column.type}`)."
    return f"**{label}** is not available for editing in this app."


def _status_options_for_column(db: NotionRecipesDB, column_name: str) -> tuple[str, ...]:
    notion_options = db.get_select_options(column_name)
    if notion_options:
        allowed = set(notion_options)
        filtered = [opt for opt in MEAL_PLAN_STATUS_OPTIONS if opt in allowed]
        if filtered:
            return tuple(filtered)
        return tuple(notion_options)
    return MEAL_PLAN_STATUS_OPTIONS


def meal_plan_status_editor_context(db: NotionRecipesDB) -> MealPlanStatusEditorContext | None:
    column = meal_plan_status_column_name(db)
    if not column:
        return None
    options = _status_options_for_column(db, column)
    if not options:
        return None
    return MealPlanStatusEditorContext(column_name=column, options=options)


def meal_plan_status_select_key(scope: str, recipe_name: str) -> str:
    digest = hashlib.sha256(recipe_name.strip().lower().encode()).hexdigest()[:16]
    return f"meal_plan_status_{scope}_{digest}"


def meal_plan_status_apply_key(scope: str, recipe_name: str) -> str:
    digest = hashlib.sha256(recipe_name.strip().lower().encode()).hexdigest()[:16]
    return f"meal_plan_status_apply_{scope}_{digest}"


def try_update_meal_plan_status(
    db: NotionRecipesDB,
    recipe: Recipe,
    *,
    new_status: str,
    context: MealPlanStatusEditorContext,
) -> bool:
    """Persist status when it changed. Returns True if Notion was updated."""
    current = meal_plan_status(recipe, status_column=context.column_name)
    if new_status == current:
        return False
    db.update_recipe(recipe.page_id, {context.column_name: new_status})
    return True


def render_meal_plan_status_unavailable(db: NotionRecipesDB) -> None:
    message = meal_plan_status_unavailable_message(db)
    if message:
        st.info(message)


def render_meal_plan_status_for_recipe(
    db: NotionRecipesDB,
    recipe: Recipe,
    *,
    scope: str,
    disabled: bool = False,
    disabled_reason: str | None = None,
) -> None:
    """Select + explicit apply for one recipe's meal-plan status."""
    context = meal_plan_status_editor_context(db)
    if context is None:
        return

    current = meal_plan_status(recipe, status_column=context.column_name)
    select_key = meal_plan_status_select_key(scope, recipe.name)
    if select_key not in st.session_state:
        st.session_state[select_key] = current

    st.selectbox(
        "Meal plan status",
        options=list(context.options),
        key=select_key,
        disabled=disabled,
        help=(
            "Active and Favorite recipes appear in auto-suggest; Paused is excluded from "
            "suggest; Deprecated is hidden from manual pick."
        ),
    )
    if disabled and disabled_reason:
        st.caption(disabled_reason)

    apply_disabled = disabled or st.session_state.get(select_key) == current
    if st.button(
        "Apply meal plan status",
        key=meal_plan_status_apply_key(scope, recipe.name),
        disabled=apply_disabled,
        help="Writes the selected status to Notion.",
    ):
        new_status = str(st.session_state.get(select_key, current))
        with loading_indicator(f"Updating meal-plan status for **{recipe.name}**…"):
            updated = try_update_meal_plan_status(
                db,
                recipe,
                new_status=new_status,
                context=context,
            )
        if updated:
            invalidate_notion_cache()
            st.success(f"Meal plan status for **{recipe.name}** is now **{new_status}**.")
            st.rerun()
        else:
            st.info(f"**{recipe.name}** already has meal-plan status **{current}**.")
