"""Notion-backed meal-plan stats and rotation status for recipes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.grocery_wizard.integrations.notion import Recipe, recipe_lookup_key

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import NotionRecipesDB

DEFAULT_SUGGESTION_REJECTIONS_COLUMN = "Suggestion rejections"
DEFAULT_PLAN_SELECTIONS_COLUMN = "Plan selections"
DEFAULT_MEAL_PLAN_STATUS_COLUMN = "Meal plan status"

STATUS_ACTIVE = "Active"
STATUS_FAVORITE = "Favorite"
STATUS_PAUSED = "Paused"
STATUS_DEPRECATED = "Deprecated"

MEAL_PLAN_STATUS_OPTIONS = (
    STATUS_ACTIVE,
    STATUS_FAVORITE,
    STATUS_PAUSED,
    STATUS_DEPRECATED,
)

FAVORITE_PICK_WEIGHT_MULTIPLIER = 2.0
REJECTION_PICK_PENALTY = 0.75

SlotOrigin = str  # "pinned" | "suggested" | "manual"


def _configured_column_name(configured: str | None, default: str) -> str:
    return (configured or default).strip()


def suggestion_rejections_column_name(db: NotionRecipesDB) -> str | None:
    name = _configured_column_name(
        db._config.suggestion_rejections_column,
        DEFAULT_SUGGESTION_REJECTIONS_COLUMN,
    )
    column = db.schema.all_columns.get(name)
    if column and column.type == "number":
        return name
    return None


def plan_selections_column_name(db: NotionRecipesDB) -> str | None:
    name = _configured_column_name(
        db._config.plan_selections_column,
        DEFAULT_PLAN_SELECTIONS_COLUMN,
    )
    column = db.schema.all_columns.get(name)
    if column and column.type == "number":
        return name
    return None


def meal_plan_status_column_name(db: NotionRecipesDB) -> str | None:
    name = _configured_column_name(
        db._config.meal_plan_status_column,
        DEFAULT_MEAL_PLAN_STATUS_COLUMN,
    )
    column = db.schema.all_columns.get(name)
    if column and column.type in ("select", "status"):
        return name
    return None


def meal_plan_status(recipe: Recipe, *, status_column: str | None) -> str:
    if not status_column:
        return STATUS_ACTIVE
    raw = recipe.properties.get(status_column)
    if raw is None or raw == "":
        return STATUS_ACTIVE
    return str(raw)


def suggestion_rejection_count(recipe: Recipe, *, rejections_column: str | None) -> int:
    if not rejections_column:
        return 0
    raw = recipe.properties.get(rejections_column)
    if raw is None:
        return 0
    try:
        return max(0, int(float(raw)))
    except (TypeError, ValueError):
        return 0


def recipe_eligible_for_auto_suggest(
    recipe: Recipe,
    *,
    status_column: str | None,
) -> bool:
    status = meal_plan_status(recipe, status_column=status_column)
    return status not in (STATUS_PAUSED, STATUS_DEPRECATED)


def recipe_eligible_for_manual_pick(
    recipe: Recipe,
    *,
    status_column: str | None,
) -> bool:
    status = meal_plan_status(recipe, status_column=status_column)
    return status != STATUS_DEPRECATED


def filter_recipes_for_auto_suggest(
    recipes: list[Recipe],
    *,
    status_column: str | None,
) -> list[Recipe]:
    return [
        recipe
        for recipe in recipes
        if recipe_eligible_for_auto_suggest(recipe, status_column=status_column)
    ]


def filter_recipes_for_manual_pick(
    recipes: list[Recipe],
    *,
    status_column: str | None,
) -> list[Recipe]:
    return [
        recipe
        for recipe in recipes
        if recipe_eligible_for_manual_pick(recipe, status_column=status_column)
    ]


def pick_weight_status_multiplier(recipe: Recipe, *, status_column: str | None) -> float:
    if meal_plan_status(recipe, status_column=status_column) == STATUS_FAVORITE:
        return FAVORITE_PICK_WEIGHT_MULTIPLIER
    return 1.0


def pick_weight_rejection_penalty(
    recipe: Recipe,
    *,
    rejections_column: str | None,
) -> float:
    count = suggestion_rejection_count(recipe, rejections_column=rejections_column)
    return count * REJECTION_PICK_PENALTY


def _recipe_by_name(recipes: list[Recipe]) -> dict[str, Recipe]:
    return {recipe_lookup_key(recipe.name): recipe for recipe in recipes}


def increment_suggestion_rejections(
    db: NotionRecipesDB,
    recipe_names: set[str] | list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> int:
    """Increment rejection counter for each named recipe. Returns number of Notion updates."""
    column = suggestion_rejections_column_name(db)
    if column is None or not recipe_names:
        return 0
    rows = cached_recipes if cached_recipes is not None else db.query_recipes()
    by_name = _recipe_by_name(rows)
    updated = 0
    for name in recipe_names:
        recipe = by_name.get(recipe_lookup_key(name))
        if recipe is None:
            continue
        current = suggestion_rejection_count(recipe, rejections_column=column)
        db.update_recipe(recipe.page_id, {column: current + 1})
        updated += 1
    return updated


def increment_plan_selections(
    db: NotionRecipesDB,
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> int:
    """Increment plan selection counter once per recipe name. Returns number of Notion updates."""
    column = plan_selections_column_name(db)
    if column is None or not recipe_names:
        return 0
    rows = cached_recipes if cached_recipes is not None else db.query_recipes()
    by_name = _recipe_by_name(rows)
    seen: set[str] = set()
    updated = 0
    for name in recipe_names:
        key = recipe_lookup_key(name)
        if key in seen:
            continue
        seen.add(key)
        recipe = by_name.get(key)
        if recipe is None:
            continue
        raw = recipe.properties.get(column)
        current = 0 if raw is None else int(float(raw))
        db.update_recipe(recipe.page_id, {column: current + 1})
        updated += 1
    return updated


def resolve_slot_origins_for_plan(
    plan_names: list[str],
    *,
    locked_names: set[str],
) -> list[SlotOrigin]:
    """Classify each slot after auto-build: pinned vs auto-suggested."""
    origins: list[SlotOrigin] = []
    for name in plan_names:
        if name in locked_names:
            origins.append("pinned")
        else:
            origins.append("suggested")
    return origins


def rejection_names_from_swap(
    plan_names: list[str],
    names_to_replace: list[str],
    slot_origins: list[SlotOrigin],
) -> set[str]:
    """Recipe names that qualify for a rejection increment when swapped away."""
    replace_set = set(names_to_replace)
    rejected: set[str] = set()
    for index, name in enumerate(plan_names):
        if name not in replace_set:
            continue
        origin = slot_origins[index] if index < len(slot_origins) else "suggested"
        if origin == "suggested":
            rejected.add(name)
    return rejected


def origins_after_swap(
    plan_names: list[str],
    names_to_replace: list[str],
    slot_origins: list[SlotOrigin],
    updated_names: list[str],
) -> list[SlotOrigin]:
    """New slot origins after replace_meals_in_plan (replacements stay suggested)."""
    replace_set = set(names_to_replace)
    origins = list(slot_origins)
    while len(origins) < len(updated_names):
        origins.append("suggested")
    for index, (before, after) in enumerate(zip(plan_names, updated_names, strict=False)):
        if before in replace_set and before != after:
            origins[index] = "suggested"
    return origins[: len(updated_names)]
