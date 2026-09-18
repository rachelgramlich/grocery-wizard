"""Dev-mode jump-to-step helpers for faster manual UI UAT."""

from __future__ import annotations

import random
from enum import StrEnum
from typing import Any

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from src.grocery_wizard.ui.grocery_flow import (
    GROCERY_STASH_NOTION_GENERATION_KEY,
    clear_grocery_session_overrides,
    default_pre_build_grocery_options,
    stash_grocery_result,
    stash_recipe_review,
)

DEFAULT_DEV_MEAL_COUNT = 1
_DEV_MEAL_PICK_SEED = 142
DEV_MANUAL_RECIPES_KEY = "dev_jump_manual_recipes"
_DEV_MANUAL_RECIPES_FP_KEY = "_dev_jump_manual_recipes_fingerprint"


class DevJumpTarget(StrEnum):
    MEALS_FILLED = "meals_filled"
    PRE_BUILD_GROCERY = "pre_build_grocery"
    PER_RECIPE_REVIEW = "per_recipe_review"
    GROCERY_RESULT = "grocery_result"


DEV_JUMP_FLOW_ORDER: tuple[DevJumpTarget, ...] = (
    DevJumpTarget.MEALS_FILLED,
    DevJumpTarget.PRE_BUILD_GROCERY,
    DevJumpTarget.PER_RECIPE_REVIEW,
    DevJumpTarget.GROCERY_RESULT,
)


def dev_jump_display_title(target: DevJumpTarget) -> str:
    return {
        DevJumpTarget.MEALS_FILLED: "Meals filled",
        DevJumpTarget.PRE_BUILD_GROCERY: "Pre-build grocery",
        DevJumpTarget.PER_RECIPE_REVIEW: "Per-recipe review",
        DevJumpTarget.GROCERY_RESULT: "Final list",
    }[target]


DEV_JUMP_CAPTIONS: dict[DevJumpTarget, str] = {
    DevJumpTarget.MEALS_FILLED: (
        "Meal plan list (section **1. Meals**) — pick recipes in the multiselect (updates "
        "meals live) or use **auto** for the default sample."
    ),
    DevJumpTarget.PRE_BUILD_GROCERY: (
        "Grocery setup (section **2. Grocery list**) — options expander and "
        "**Create grocery list**."
    ),
    DevJumpTarget.PER_RECIPE_REVIEW: (
        "Per-recipe ingredient review — edit lines in expanders before the list is built."
    ),
    DevJumpTarget.GROCERY_RESULT: (
        "Final list — built grocery list with re-add/remove, copy, and meals."
    ),
}


def dev_manual_recipes_fingerprint(names: list[str]) -> tuple[str, ...]:
    return tuple(name.strip().lower() for name in names if name.strip())


def resolve_dev_jump_meal_names(
    session_state: Any,
    db: NotionRecipesDB,
    *,
    meal_count: int,
    force_auto: bool = False,
) -> list[str]:
    """Manual multiselect wins over auto sample unless *force_auto* is True."""
    if not force_auto:
        manual = session_state.get(DEV_MANUAL_RECIPES_KEY) or []
        cleaned_manual = [name for name in manual if name.strip()]
        if cleaned_manual:
            return cleaned_manual
    return pick_default_recipe_names(db.query_recipes(), meal_count=meal_count)


def sync_dev_manual_multiselect(session_state: Any) -> None:
    """When dev manual recipe pick changes, align the meal plan and drop stale grocery UI."""
    manual = list(session_state.get(DEV_MANUAL_RECIPES_KEY) or [])
    fingerprint = dev_manual_recipes_fingerprint(manual)
    previous = session_state.get(_DEV_MANUAL_RECIPES_FP_KEY)
    if previous is not None and fingerprint == previous:
        return

    session_state[_DEV_MANUAL_RECIPES_FP_KEY] = fingerprint
    if not manual:
        return

    clear_grocery_flow_state(session_state)
    session_state["plan_meals_text"] = "\n".join(manual)
    session_state["plan_prebuild_pinned_recipes"] = list(manual)
    session_state.pop("plan_rejected_names", None)
    session_state.pop("weekly_plan_last_saved_name", None)
    session_state.pop("weekly_plan_saved_fingerprint", None)


def pick_default_recipe_names(
    all_recipes: list[Recipe],
    *,
    meal_count: int = DEFAULT_DEV_MEAL_COUNT,
) -> list[str]:
    """Pick a small set of Notion recipes with ingredients for dev jumps."""
    with_ingredients = [recipe for recipe in all_recipes if (recipe.ingredients or "").strip()]
    pool = with_ingredients or list(all_recipes)
    if not pool:
        return []
    rng = random.Random(_DEV_MEAL_PICK_SEED)
    shuffled = sorted(pool, key=lambda recipe: recipe.name.lower())
    rng.shuffle(shuffled)
    return [recipe.name for recipe in shuffled[:meal_count]]


def clear_grocery_flow_state(session_state: Any) -> None:
    """Drop grocery result, review UI, and run-scoped pantry/recurring overrides."""
    for key in (
        "grocery_result",
        "grocery_readd",
        "grocery_remove_once",
        "grocery_final_list",
        "grocery_final_list_fingerprint",
        "meals_final_list",
        "meals_final_list_fingerprint",
        "grocery_per_recipe_review",
        "grocery_review_baseline",
        "grocery_review_options",
        "grocery_review_recipes",
        "grocery_review_plan_fingerprint",
        "grocery_review_baseline",
        "grocery_review_save_to_notion",
        GROCERY_STASH_NOTION_GENERATION_KEY,
    ):
        session_state.pop(key, None)
    for key in list(session_state.keys()):
        if str(key).startswith("review_ing_"):
            session_state.pop(key, None)
    clear_grocery_session_overrides(session_state)


def commit_dev_jump(
    session_state: Any,
    db: NotionRecipesDB,
    target: DevJumpTarget,
    names: list[str],
) -> list[str]:
    """Apply a dev jump after recipe names are chosen; returns ``names`` used."""
    cleaned = [name for name in names if name.strip()]
    if not cleaned:
        return []

    clear_grocery_flow_state(session_state)
    session_state["plan_meals_text"] = "\n".join(cleaned)
    session_state.pop("plan_rejected_names", None)
    session_state.pop("weekly_plan_last_saved_name", None)
    session_state.pop("weekly_plan_saved_fingerprint", None)

    if target in (DevJumpTarget.MEALS_FILLED, DevJumpTarget.PRE_BUILD_GROCERY):
        return cleaned

    grocery_options = default_pre_build_grocery_options(session_state)
    recipes = db.query_recipes()

    if target == DevJumpTarget.PER_RECIPE_REVIEW:
        stash_recipe_review(session_state, cleaned, recipes, grocery_options)
        return cleaned

    if target == DevJumpTarget.GROCERY_RESULT:
        stash_grocery_result(session_state, db, cleaned, grocery_options, recipes=recipes)
        return cleaned

    return cleaned


def apply_dev_jump(
    session_state: Any,
    db: NotionRecipesDB,
    target: DevJumpTarget,
    *,
    meal_count: int = DEFAULT_DEV_MEAL_COUNT,
    recipe_names: list[str] | None = None,
) -> list[str]:
    """Resolve recipe names then commit the jump (CLI/tests helper)."""
    if recipe_names is not None:
        names = list(recipe_names)
    else:
        names = resolve_dev_jump_meal_names(session_state, db, meal_count=meal_count)
    return commit_dev_jump(session_state, db, target, names)
