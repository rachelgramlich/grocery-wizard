"""Meal-plan filter widgets shared by weekly planning."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.planning.meal_planner import MealPlanFilters
from src.grocery_wizard.recipes.weeknight import DEFAULT_WEEKNIGHT_COLUMN


def recipes_ingredient_cache_key(recipes: list) -> tuple[tuple[str, str], ...]:
    return tuple((recipe.page_id, recipe.ingredients or "") for recipe in recipes)


def ingredient_options_from_index(ingredient_index: dict[str, set[str]]) -> list[str]:
    return sorted({name for names in ingredient_index.values() for name in names})


def week_level_plan_filter_columns(schema: DatabaseSchema) -> list[ColumnInfo]:
    columns: list[ColumnInfo] = []
    meal = schema.all_columns.get("Meal")
    if meal is not None:
        columns.append(meal)
    weeknight = schema.all_columns.get(DEFAULT_WEEKNIGHT_COLUMN)
    if weeknight is not None:
        columns.append(weeknight)
    return columns


def _render_column_filter(
    column: ColumnInfo,
    defaults: MealPlanFilters,
    *,
    key_prefix: str,
) -> Any:
    default_val = defaults.values.get(column.name)
    if column.type in ("select", "status"):
        options = ["Any", *column.options]
        current = default_val if default_val in column.options else "Any"
        picked = st.selectbox(
            column.name,
            options,
            index=options.index(current),
            key=f"{key_prefix}_{column.name}",
        )
        if picked != "Any":
            return picked
        return None
    if column.type == "multi_select":
        default_list = default_val if isinstance(default_val, list) else []
        picked = st.multiselect(
            column.name,
            column.options,
            default=default_list,
            key=f"{key_prefix}_{column.name}",
        )
        return picked or None
    if column.type == "checkbox":
        checked = st.checkbox(
            column.name,
            value=bool(default_val) if isinstance(default_val, bool) else False,
            key=f"{key_prefix}_{column.name}",
        )
        if isinstance(default_val, bool):
            return checked
        if checked:
            return True
    return None


def render_meal_plan_filters(
    filter_columns: list[ColumnInfo],
    defaults: MealPlanFilters,
    *,
    key_prefix: str,
    ingredient_index: dict[str, set[str]] | None = None,
) -> MealPlanFilters:
    values: dict[str, Any] = {}
    select_columns = [column for column in filter_columns if column.type != "checkbox"]
    checkbox_columns = [column for column in filter_columns if column.type == "checkbox"]

    for column in select_columns:
        picked = _render_column_filter(column, defaults, key_prefix=key_prefix)
        if picked is not None:
            values[column.name] = picked

    ingredient_names: list[str] = []
    ingredient_mode = "include"

    if ingredient_index is not None:
        ingredient_options = ingredient_options_from_index(ingredient_index)
        help_text = (
            f"{len(ingredient_options)} ingredients from your recipes"
            if ingredient_options
            else None
        )
        ingredient_names = st.multiselect(
            "Ingredients",
            ingredient_options,
            default=[],
            key=f"{key_prefix}_ingredient_names",
            help=help_text,
        )
        if ingredient_names:
            ingredient_mode = st.radio(
                "Filter mode",
                options=["include", "exclude"],
                format_func=lambda m: (
                    "Include recipes with any selected ingredient"
                    if m == "include"
                    else "Exclude recipes with any selected ingredient"
                ),
                index=0,
                key=f"{key_prefix}_ingredient_mode",
                label_visibility="collapsed",
            )

    for column in checkbox_columns:
        picked = _render_column_filter(column, defaults, key_prefix=key_prefix)
        if picked is not None:
            values[column.name] = picked

    return MealPlanFilters(
        values=values,
        ingredient_names=list(ingredient_names),
        ingredient_mode=ingredient_mode,
    )
