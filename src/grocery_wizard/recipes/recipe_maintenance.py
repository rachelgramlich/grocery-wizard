"""Batch backfill for existing Notion recipe rows (ingredients and metadata)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.grocery_wizard.ingredients.parsed import is_nyt_cooking_url
from src.grocery_wizard.ingredients.sync import prepare_ingredients_for_notion
from src.grocery_wizard.integrations.notion import (
    ColumnInfo,
    DatabaseSchema,
    NotionFieldValues,
    NotionRecipesDB,
    Recipe,
)
from src.grocery_wizard.recipes.add_recipe import _weeknight_column_name
from src.grocery_wizard.recipes.classify import classify_recipe
from src.grocery_wizard.recipes.scraper import ScrapeError, ingredients_to_text, scrape_recipe
from src.grocery_wizard.recipes.weeknight import is_weeknight_friendly

_LUNCH_DINNER_MEALS = frozenset({"Lunch", "Dinner"})

ProgressCallback = Callable[[str], None]
FractionCallback = Callable[[float], None]


@dataclass(slots=True)
class BackfillSummary:
    """Counts for a backfill run."""

    scanned: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    messages: list[str] = field(default_factory=list)


def recipe_has_link(recipe: Recipe) -> bool:
    return bool((recipe.link or "").strip())


def ingredients_text(recipe: Recipe) -> str:
    return (recipe.ingredients or "").strip()


def recipe_missing_ingredients(recipe: Recipe, schema: DatabaseSchema) -> bool:
    if not schema.ingredients_column:
        return False
    if not recipe_has_link(recipe):
        return False
    return not ingredients_text(recipe)


def recipes_missing_ingredients(recipes: list[Recipe], schema: DatabaseSchema) -> list[Recipe]:
    return [recipe for recipe in recipes if recipe_missing_ingredients(recipe, schema)]


def recipe_manual_ingredients_in_notion(recipe: Recipe, schema: DatabaseSchema) -> bool:
    """No link and no ingredients — cannot auto-backfill; edit both in Notion."""
    if not schema.ingredients_column:
        return not recipe_has_link(recipe)
    return not recipe_has_link(recipe) and not ingredients_text(recipe)


def recipes_manual_ingredients_in_notion(
    recipes: list[Recipe],
    schema: DatabaseSchema,
) -> list[Recipe]:
    return [recipe for recipe in recipes if recipe_manual_ingredients_in_notion(recipe, schema)]


def recipe_possibly_missing_all_checkboxes(recipe: Recipe, schema: DatabaseSchema) -> bool:
    """All review checkboxes unchecked — may be intentional; shown as *possibly* missing."""
    if not schema.checkbox_columns:
        return False
    return all(not bool(recipe.properties.get(col.name)) for col in schema.checkbox_columns)


def recipes_possibly_missing_all_checkboxes(
    recipes: list[Recipe],
    schema: DatabaseSchema,
) -> list[Recipe]:
    return [recipe for recipe in recipes if recipe_possibly_missing_all_checkboxes(recipe, schema)]


def normalize_meal_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    text = str(value).strip()
    return {text} if text else set()


def meal_values_on_recipe(recipe: Recipe, schema: DatabaseSchema) -> set[str]:
    for col in schema.filter_columns:
        if col.name.lower() == "meal":
            return normalize_meal_values(recipe.properties.get(col.name))
    return set()


def metadata_filter_columns_for_meals(
    schema: DatabaseSchema,
    meals: set[str],
) -> list[ColumnInfo]:
    """Which select/multi columns to scan or fill for a known (or unknown) meal set."""
    unknown_meal = not meals
    columns: list[ColumnInfo] = []
    for col in schema.filter_columns:
        key = col.name.lower()
        if key in ("meal", "cuisine"):
            columns.append(col)
        elif key == "protein":
            if unknown_meal or meals & _LUNCH_DINNER_MEALS:
                columns.append(col)
        elif key == "dinner category":
            if unknown_meal or "Dinner" in meals:
                columns.append(col)
        elif key == "tags":
            if unknown_meal or meals != {"Drink"}:
                columns.append(col)
        elif unknown_meal or meals & _LUNCH_DINNER_MEALS:
            columns.append(col)
    return columns


def metadata_checkbox_columns_for_meals(
    schema: DatabaseSchema,
    meals: set[str],
) -> list[ColumnInfo]:
    """Weeknight friendly only when Meal includes Dinner."""
    if "Dinner" not in meals:
        return []
    weeknight_column = _weeknight_column_name(schema)
    if not weeknight_column:
        return []
    return [col for col in schema.checkbox_columns if col.name == weeknight_column]


def metadata_backfill_columns_for_recipe(
    recipe: Recipe,
    schema: DatabaseSchema,
) -> list[ColumnInfo]:
    meals = meal_values_on_recipe(recipe, schema)
    return [
        *metadata_filter_columns_for_meals(schema, meals),
        *metadata_checkbox_columns_for_meals(schema, meals),
    ]


def metadata_column_names(schema: DatabaseSchema) -> list[str]:
    """Filter column names considered for metadata backfill when meal is unknown."""
    return [col.name for col in metadata_filter_columns_for_meals(schema, set())]


def is_blank_metadata_value(column_type: str, value: Any) -> bool:
    if value is None:
        return True
    if column_type in ("select", "status"):
        return not str(value).strip()
    if column_type == "multi_select":
        if not isinstance(value, list):
            return True
        return len(value) == 0 or all(not str(item).strip() for item in value)
    return False


def is_blank_checkbox_value(value: Any) -> bool:
    return not bool(value)


def _column_is_blank(col: ColumnInfo, value: Any) -> bool:
    if col.type == "checkbox":
        return is_blank_checkbox_value(value)
    return is_blank_metadata_value(col.type, value)


def recipe_missing_metadata(recipe: Recipe, schema: DatabaseSchema) -> bool:
    """Link + ingredients, with an empty meal-aware metadata column."""
    if not recipe_has_link(recipe):
        return False
    if not ingredients_text(recipe):
        return False
    for col in metadata_backfill_columns_for_recipe(recipe, schema):
        if _column_is_blank(col, recipe.properties.get(col.name)):
            return True
    return False


def recipes_missing_metadata(recipes: list[Recipe], schema: DatabaseSchema) -> list[Recipe]:
    return [recipe for recipe in recipes if recipe_missing_metadata(recipe, schema)]


def _ingredient_lines(recipe: Recipe) -> list[str]:
    return [line.strip() for line in ingredients_text(recipe).splitlines() if line.strip()]


def _blank_metadata_updates(
    recipe: Recipe,
    schema: DatabaseSchema,
    inferred: NotionFieldValues,
    *,
    eligible_names: set[str],
) -> NotionFieldValues:
    updates: NotionFieldValues = {}
    columns_by_name = {col.name: col for col in [*schema.filter_columns, *schema.checkbox_columns]}
    for name in eligible_names:
        col = columns_by_name.get(name)
        if col is None or name not in inferred:
            continue
        current = recipe.properties.get(col.name)
        if not _column_is_blank(col, current):
            continue
        value = inferred[name]
        if value is None or value in ("", []):
            continue
        updates[name] = value
    return updates


def _resolve_total_minutes(
    url: str,
    *,
    nyt_client: Any | None,
) -> float | None:
    if nyt_client is not None and is_nyt_cooking_url(url):
        from src.grocery_wizard.integrations.nyt_cooking import _fetch_nyt_total_minutes

        minutes = _fetch_nyt_total_minutes(nyt_client, "", url)
        if minutes is not None:
            return minutes
    try:
        scraped = scrape_recipe(url)
    except ScrapeError:
        return None
    else:
        return scraped.total_time_minutes


def infer_metadata_field_values(
    db: NotionRecipesDB,
    recipe: Recipe,
    *,
    nyt_client: Any | None = None,
) -> NotionFieldValues:
    schema = db.schema
    url = (recipe.link or "").strip()
    filter_columns = [(col.name, col.type, col.options) for col in schema.filter_columns]
    total_minutes = _resolve_total_minutes(url, nyt_client=nyt_client)
    inferred = classify_recipe(
        recipe.name,
        _ingredient_lines(recipe),
        filter_columns,
        total_minutes=total_minutes,
        weeknight_column=None,
    )

    meals = meal_values_on_recipe(recipe, schema)
    meals |= normalize_meal_values(inferred.get("Meal"))

    if "Dinner" in meals:
        weeknight_column = _weeknight_column_name(schema)
        if weeknight_column:
            inferred[weeknight_column] = is_weeknight_friendly(
                recipe.name,
                meal="Dinner",
                total_minutes=total_minutes,
            )

    eligible_names = {col.name for col in metadata_filter_columns_for_meals(schema, meals)}
    eligible_names |= {col.name for col in metadata_checkbox_columns_for_meals(schema, meals)}

    return _blank_metadata_updates(
        recipe,
        schema,
        inferred,
        eligible_names=eligible_names,
    )


def format_backfill_summary(label: str, summary: BackfillSummary) -> str:
    return (
        f"{label}: {summary.succeeded} updated, "
        f"{summary.failed} failed, {summary.skipped} skipped "
        f"(of {summary.scanned} scanned)"
    )


def run_ingredients_backfill(
    db: NotionRecipesDB,
    candidates: list[Recipe],
    *,
    on_progress: ProgressCallback | None = None,
    on_fraction: FractionCallback | None = None,
) -> BackfillSummary:
    schema = db.schema
    summary = BackfillSummary(scanned=len(candidates))
    if not schema.ingredients_column:
        summary.skipped = len(candidates)
        return summary

    total = len(candidates)
    for index, recipe in enumerate(candidates, start=1):
        if on_fraction and total:
            on_fraction(index / total)

        url = (recipe.link or "").strip()
        if not url:
            summary.skipped += 1
            if on_progress:
                on_progress(f"Skipped (no link): {recipe.name}")
            continue

        if on_progress:
            on_progress(f"Scraping ingredients: {recipe.name}")

        try:
            scraped = scrape_recipe(url)
        except ScrapeError as exc:
            summary.failed += 1
            if on_progress:
                on_progress(f"Failed: {recipe.name} — {exc}")
            continue

        if not scraped.ingredients:
            summary.skipped += 1
            if on_progress:
                on_progress(f"Skipped (no ingredients on page): {recipe.name}")
            continue

        ingredients_text_value = prepare_ingredients_for_notion(
            ingredients_to_text(scraped.ingredients),
            source_url=url,
        )
        db.update_recipe(
            recipe.page_id,
            {schema.ingredients_column: ingredients_text_value},
        )
        summary.succeeded += 1
        if on_progress:
            on_progress(f"Updated ingredients: {recipe.name}")

    if on_fraction:
        on_fraction(1.0)
    return summary


def run_metadata_backfill(
    db: NotionRecipesDB,
    candidates: list[Recipe],
    *,
    nyt_client: Any | None = None,
    on_progress: ProgressCallback | None = None,
    on_fraction: FractionCallback | None = None,
) -> BackfillSummary:
    summary = BackfillSummary(scanned=len(candidates))
    total = len(candidates)

    for index, recipe in enumerate(candidates, start=1):
        if on_fraction and total:
            on_fraction(index / total)

        url = (recipe.link or "").strip()
        if not url:
            summary.skipped += 1
            if on_progress:
                on_progress(f"Skipped (no link): {recipe.name}")
            continue

        if on_progress:
            on_progress(f"Inferring metadata: {recipe.name}")

        try:
            updates = infer_metadata_field_values(db, recipe, nyt_client=nyt_client)
        except Exception as exc:
            summary.failed += 1
            if on_progress:
                on_progress(f"Failed: {recipe.name} — {exc}")
            continue

        if not updates:
            summary.skipped += 1
            if on_progress:
                on_progress(f"Skipped (nothing to fill): {recipe.name}")
            continue

        db.update_recipe(recipe.page_id, updates)
        summary.succeeded += 1
        detail = ", ".join(f"{key}={value!r}" for key, value in updates.items())
        if on_progress:
            on_progress(f"Updated metadata: {recipe.name} ({detail})")

    if on_fraction:
        on_fraction(1.0)
    return summary
