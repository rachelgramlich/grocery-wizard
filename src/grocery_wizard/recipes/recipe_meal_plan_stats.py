"""Notion-backed meal-plan stats and rotation status for recipes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.grocery_wizard.integrations.notion import Recipe, recipe_lookup_key

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import ColumnInfo, NotionRecipesDB

DEFAULT_REJECTION_COUNT_COLUMN = "Rejection count"
DEFAULT_SELECTION_COUNT_COLUMN = "Selection count"
DEFAULT_MEAL_PLAN_STATUS_COLUMN = "Meal plan status"

# Legacy names (pre-rename); still recognized when reading schema / env overrides.
LEGACY_REJECTION_COUNT_COLUMN = "Suggestion rejections"
LEGACY_SELECTION_COUNT_COLUMN = "Plan selections"


def meal_plan_tracking_column_names() -> frozenset[str]:
    """Notion columns owned by meal-plan stats — never auto-classified or backfilled."""
    return frozenset(
        {
            DEFAULT_REJECTION_COUNT_COLUMN,
            DEFAULT_SELECTION_COUNT_COLUMN,
            DEFAULT_MEAL_PLAN_STATUS_COLUMN,
            LEGACY_REJECTION_COUNT_COLUMN,
            LEGACY_SELECTION_COUNT_COLUMN,
        }
    )


def is_meal_plan_tracking_column(column_name: str) -> bool:
    return column_name in meal_plan_tracking_column_names()


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


def rejection_count_column_name(db: NotionRecipesDB) -> str | None:
    name = _configured_column_name(
        db._config.suggestion_rejections_column,
        DEFAULT_REJECTION_COUNT_COLUMN,
    )
    column = db.schema.all_columns.get(name)
    if column and column.type == "number":
        return name
    return None


def selection_count_column_name(db: NotionRecipesDB) -> str | None:
    name = _configured_column_name(
        db._config.plan_selections_column,
        DEFAULT_SELECTION_COUNT_COLUMN,
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


def meal_plan_status_is_empty(recipe: Recipe, *, status_column: str | None) -> bool:
    if not status_column:
        return False
    raw = recipe.properties.get(status_column)
    if raw is None:
        return True
    return str(raw).strip() == ""


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


def _legacy_number_column(db: NotionRecipesDB, legacy_name: str) -> str | None:
    column = db.schema.all_columns.get(legacy_name)
    if column and column.type == "number":
        return legacy_name
    return None


def filter_columns_for_recipe_classify(
    filter_columns: list[ColumnInfo],
) -> list[tuple[str, str, list[str]]]:
    """Drop meal-plan tracking selects from classify / metadata inference."""
    return [
        (col.name, col.type, col.options)
        for col in filter_columns
        if not is_meal_plan_tracking_column(col.name)
    ]


def _recipe_by_name(recipes: list[Recipe]) -> dict[str, Recipe]:
    return {recipe_lookup_key(recipe.name): recipe for recipe in recipes}


def increment_rejection_count(
    db: NotionRecipesDB,
    recipe_names: set[str] | list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> int:
    """Increment rejection counter for each named recipe. Returns number of Notion updates."""
    column = rejection_count_column_name(db)
    if column is None:
        column = _legacy_number_column(db, LEGACY_REJECTION_COUNT_COLUMN)
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


def increment_selection_count(
    db: NotionRecipesDB,
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> int:
    """Increment plan selection counter once per recipe name.

    When the selection count bumps, also sets Meal plan status to Active if that
    select is empty — the only automatic write path for status (no bulk backfill).
    """
    selection_column = selection_count_column_name(db)
    if selection_column is None:
        selection_column = _legacy_number_column(db, LEGACY_SELECTION_COUNT_COLUMN)
    status_column = meal_plan_status_column_name(db)
    if selection_column is None and status_column is None:
        return 0
    if not recipe_names:
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
        updates: dict[str, object] = {}
        if selection_column is not None:
            raw = recipe.properties.get(selection_column)
            current = 0 if raw is None else int(float(raw))
            updates[selection_column] = current + 1
        if status_column is not None and meal_plan_status_is_empty(
            recipe, status_column=status_column
        ):
            updates[status_column] = STATUS_ACTIVE
        if not updates:
            continue
        db.update_recipe(recipe.page_id, updates)
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


# Backward-compatible aliases (PR #296 names).
increment_suggestion_rejections = increment_rejection_count
increment_plan_selections = increment_selection_count
suggestion_rejections_column_name = rejection_count_column_name
plan_selections_column_name = selection_count_column_name
