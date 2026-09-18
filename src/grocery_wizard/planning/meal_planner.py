"""Meal planning helpers for Streamlit."""

from __future__ import annotations

__all__ = [
    "FilterValue",
    "MealPlanFilters",
    "build_ingredient_index",
    "filter_recipes",
    "load_recent_plan_names",
    "replace_meals_in_plan",
    "save_week_plan",
    "suggest_meals",
]

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.grocery_wizard.config import WEEK_PLAN_PATH
from src.grocery_wizard.ingredients.normalize import filter_ingredient_keys
from src.grocery_wizard.ingredients.sync import parse_ingredients_text
from src.grocery_wizard.integrations.notion import (
    ColumnInfo,
    Recipe,
    recipe_lookup_key,
)

DIVERSITY_COLUMNS = ("Protein", "Dinner Category", "Cuisine")

DEFAULT_FILTER_MEAL = "Dinner"
DEFAULT_FILTER_WEEKNIGHT_COLUMN = "Dinner: Weeknight Friendly"

# A filter value is always a string, list of strings, bool, or absent (None).
type FilterValue = str | list[str] | bool | None


@dataclass
class MealPlanFilters:
    """Per-column filter values. Omitted columns are not filtered."""

    values: dict[str, FilterValue] = field(default_factory=dict)
    ingredient_names: list[str] = field(default_factory=list)
    ingredient_mode: str = "include"  # "include" or "exclude"


def _recipe_normalized_ingredient_set(recipe: Recipe) -> set[str]:
    """Return canonical filter keys for a recipe's ingredients (meal-plan picker)."""
    raw = recipe.ingredients or ""
    if not raw.strip():
        return set()
    lines, _ = parse_ingredients_text(raw)
    result: set[str] = set()
    for line in lines:
        result.update(filter_ingredient_keys(line))
    return result


def build_ingredient_index(recipes: list[Recipe]) -> dict[str, set[str]]:
    """Return a mapping of recipe page_id → canonical meal-plan ingredient filter keys."""
    return {recipe.page_id: _recipe_normalized_ingredient_set(recipe) for recipe in recipes}


def filter_recipes(
    recipes: list[Recipe],
    filters: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    *,
    ingredient_index: dict[str, set[str]] | None = None,
) -> list[Recipe]:
    """Return recipes matching all active filters."""
    has_column_filters = bool(filters.values)
    has_ingredient_filter = bool(filters.ingredient_names)

    if not has_column_filters and not has_ingredient_filter:
        return list(recipes)

    return [
        recipe
        for recipe in recipes
        if recipe_matches_filters(
            recipe,
            filters,
            schema_columns,
            ingredient_index=ingredient_index,
        )
    ]


def recipe_matches_filters(
    recipe: Recipe,
    filters: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    *,
    ingredient_index: dict[str, set[str]] | None = None,
) -> bool:
    for column_name, filter_value in filters.values.items():
        column = schema_columns.get(column_name)
        if column is None:
            continue
        if not recipe_matches_column_filter(
            recipe.properties.get(column_name),
            filter_value,
            column.type,
        ):
            return False

    if filters.ingredient_names:
        selected = set(filters.ingredient_names)
        if ingredient_index is not None:
            recipe_ingredients = ingredient_index.get(recipe.page_id, set())
        else:
            recipe_ingredients = _recipe_normalized_ingredient_set(recipe)
        if filters.ingredient_mode == "include":
            if not recipe_ingredients & selected:
                return False
        elif recipe_ingredients & selected:
            return False

    return True


def recipe_matches_column_filter(
    prop_value: Any,
    filter_value: Any,
    column_type: str,
) -> bool:
    if filter_value is None:
        return True

    if column_type in ("select", "status"):
        return prop_value == filter_value

    if column_type == "multi_select":
        if not filter_value:
            return True
        if not isinstance(filter_value, list):
            filter_value = [filter_value]
        if not isinstance(prop_value, list):
            return False
        return any(option in prop_value for option in filter_value)

    if column_type == "checkbox":
        return prop_value is filter_value

    return True


def default_filters(schema_columns: dict[str, ColumnInfo]) -> MealPlanFilters:
    """Default meal-plan filters: Dinner + weeknight-friendly."""
    values: dict[str, Any] = {}

    meal_col = schema_columns.get("Meal")
    if meal_col is not None and (not meal_col.options or DEFAULT_FILTER_MEAL in meal_col.options):
        values["Meal"] = DEFAULT_FILTER_MEAL

    if DEFAULT_FILTER_WEEKNIGHT_COLUMN in schema_columns:
        values[DEFAULT_FILTER_WEEKNIGHT_COLUMN] = True

    return MealPlanFilters(values=values)


def _recipe_tags(recipe: Recipe, column: str) -> set[str]:
    value = recipe.properties.get(column)
    if isinstance(value, list):
        return {str(item) for item in value}
    if value is not None and value != "":
        return {str(value)}
    return set()


def _shares_tag(recipe_a: Recipe, recipe_b: Recipe, column: str) -> bool:
    tags_a = _recipe_tags(recipe_a, column)
    tags_b = _recipe_tags(recipe_b, column)
    if not tags_a or not tags_b:
        return False
    return bool(tags_a & tags_b)


TOP_K_DIVERSE_MIN = 8
TOP_K_DIVERSE_MAX = 15
RECENT_PLAN_PENALTY = 4


def _diversity_score(recipe: Recipe, selected: list[Recipe]) -> tuple[int, int, int]:
    used: dict[str, set[str]] = {col: set() for col in DIVERSITY_COLUMNS}
    for prior in selected:
        for column in DIVERSITY_COLUMNS:
            used[column].update(_recipe_tags(prior, column))

    protein_new = len(_recipe_tags(recipe, "Protein") - used["Protein"])
    category_new = len(_recipe_tags(recipe, "Dinner Category") - used["Dinner Category"])
    cuisine_new = len(_recipe_tags(recipe, "Cuisine") - used["Cuisine"])
    return (protein_new, category_new, cuisine_new)


def _diversity_total(recipe: Recipe, selected: list[Recipe]) -> int:
    return sum(_diversity_score(recipe, selected))


def _effective_top_k(candidate_count: int) -> int:
    """Scale top-k with pool size so randomness isn't confined to the same few recipes."""
    if candidate_count <= 1:
        return candidate_count
    scaled = max(TOP_K_DIVERSE_MIN, candidate_count // 2)
    return min(scaled, TOP_K_DIVERSE_MAX, candidate_count)


def _pick_weight(recipe: Recipe, selected: list[Recipe], recent_names: set[str]) -> float:
    score = float(_diversity_total(recipe, selected))
    if recipe.name in recent_names:
        score = max(0.0, score - RECENT_PLAN_PENALTY)
    return max(1.0, score + 1.0)


def eligible_suggestion_pool(
    pool: list[Recipe],
    accepted_names: set[str],
    rejected_names: set[str],
) -> list[Recipe]:
    """Recipes still available for suggestion (not accepted or rejected this session)."""
    return [
        recipe
        for recipe in pool
        if recipe.name not in accepted_names and recipe.name not in rejected_names
    ]


def pick_diverse_recipe(
    candidates: list[Recipe],
    selected: list[Recipe],
    *,
    top_k: int | None = None,
    recent_names: set[str] | None = None,
) -> Recipe:
    """Pick a recipe favoring variety, weighted-random among top diverse options."""
    if not candidates:
        raise ValueError("candidates must not be empty")
    if len(candidates) == 1:
        return candidates[0]

    pool = list(candidates)
    if selected:
        last = selected[-1]
        without_repeat = [recipe for recipe in pool if not _shares_tag(recipe, last, "Protein")]
        if without_repeat:
            pool = without_repeat

    recent = recent_names or set()
    scored = sorted(
        ((recipe, _diversity_total(recipe, selected)) for recipe in pool),
        key=lambda item: item[1],
        reverse=True,
    )
    k = top_k if top_k is not None else _effective_top_k(len(scored))
    top = scored[: min(k, len(scored))]
    recipes, weights = zip(
        *((recipe, _pick_weight(recipe, selected, recent)) for recipe, _ in top),
        strict=True,
    )
    return random.choices(list(recipes), weights=list(weights), k=1)[0]


def select_diverse_meals(
    pool: list[Recipe],
    count: int,
    *,
    recent_names: set[str] | None = None,
) -> list[Recipe]:
    """Select up to count recipes with diversified protein, category, and cuisine."""
    remaining = list(pool)
    selected: list[Recipe] = []
    for _ in range(count):
        if not remaining:
            break
        pick = pick_diverse_recipe(remaining, selected, recent_names=recent_names)
        selected.append(pick)
        remaining = [recipe for recipe in remaining if recipe.page_id != pick.page_id]
    return selected


def _resolve_locked_by_names(
    locked_names: list[str],
    all_recipes: list[Recipe],
) -> list[Recipe]:
    """Resolve locked recipe names to Recipe objects, preserving order and skipping duplicates."""
    recipe_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in all_recipes}
    locked: list[Recipe] = []
    seen_ids: set[str] = set()
    for name in locked_names:
        recipe = recipe_by_name.get(recipe_lookup_key(name))
        if recipe is None or recipe.page_id in seen_ids:
            continue
        locked.append(recipe)
        seen_ids.add(recipe.page_id)
    return locked


def load_recent_plan_names(path: Path = WEEK_PLAN_PATH) -> set[str]:
    """Recipe names from the saved week plan (last week's picks)."""
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    recipes = payload.get("recipes")
    if not isinstance(recipes, list):
        return set()
    return {name.strip() for name in recipes if isinstance(name, str) and name.strip()}


def suggest_meals(
    all_recipes: list[Recipe],
    *,
    meals: int,
    locked_names: list[str] | None = None,
    filters: MealPlanFilters | None = None,
    schema_columns: dict[str, ColumnInfo],
    rejected_names: set[str] | None = None,
    recent_names: set[str] | None = None,
    ingredient_index: dict[str, set[str]] | None = None,
) -> list[str]:
    """Suggest a meal plan: locked recipes first, then diverse auto-filled slots."""
    active_filters = filters if filters is not None else default_filters(schema_columns)
    locked_recipes = _resolve_locked_by_names(locked_names or [], all_recipes)[:meals]

    full_pool = filter_recipes(
        all_recipes, active_filters, schema_columns, ingredient_index=ingredient_index
    )
    locked_ids = {recipe.page_id for recipe in locked_recipes}
    locked_name_set = {recipe.name for recipe in locked_recipes}
    session_rejected = set(rejected_names or ())
    pool = eligible_suggestion_pool(
        [recipe for recipe in full_pool if recipe.page_id not in locked_ids],
        locked_name_set,
        session_rejected,
    )

    recent = recent_names if recent_names is not None else load_recent_plan_names()

    remaining_slots = meals - len(locked_recipes)
    suggested: list[str] = []
    if remaining_slots > 0 and pool:
        picked = select_diverse_meals(pool, remaining_slots, recent_names=recent)
        suggested = [recipe.name for recipe in picked]

    return [recipe.name for recipe in locked_recipes] + suggested


def replace_meals_in_plan(
    plan_names: list[str],
    names_to_replace: list[str],
    *,
    all_recipes: list[Recipe],
    pool: list[Recipe],
    rejected_names: set[str] | None = None,
    recent_names: set[str] | None = None,
) -> tuple[list[str], set[str]]:
    """Swap named meals for diverse alternatives, tracking rejected names for the session."""
    if not names_to_replace:
        return list(plan_names), set(rejected_names or ())

    recipe_by_name = {recipe.name: recipe for recipe in all_recipes}
    updated = list(plan_names)
    session_rejected = set(rejected_names or ())
    replace_set = set(names_to_replace)
    recent = recent_names if recent_names is not None else load_recent_plan_names()

    for index, name in enumerate(updated):
        if name not in replace_set:
            continue

        session_rejected.add(name)
        accepted_names = {plan_name for slot, plan_name in enumerate(updated) if slot != index}
        plan_recipes = [
            recipe_by_name[plan_name] for plan_name in accepted_names if plan_name in recipe_by_name
        ]
        candidates = eligible_suggestion_pool(pool, accepted_names, session_rejected)
        old_recipe = recipe_by_name.get(name)
        if old_recipe is not None:
            without_old = [recipe for recipe in candidates if recipe.page_id != old_recipe.page_id]
            if without_old:
                candidates = without_old

        if not candidates:
            continue

        replacement = pick_diverse_recipe(candidates, plan_recipes, recent_names=recent)
        updated[index] = replacement.name

    return updated, session_rejected


def save_week_plan(recipe_names: list[str], path: Path = WEEK_PLAN_PATH) -> Path:
    """Persist finalized plan for grocery_list.py."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"recipes": [name.strip() for name in recipe_names if name.strip()]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
