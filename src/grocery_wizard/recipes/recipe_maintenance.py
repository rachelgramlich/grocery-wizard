"""Batch backfill for existing Notion recipe rows (ingredients and metadata)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.grocery_wizard.ingredients.parsed import is_nyt_cooking_url
from src.grocery_wizard.ingredients.sync import prepare_ingredients_for_notion
from src.grocery_wizard.integrations.notion import (
    DatabaseSchema,
    NotionFieldValues,
    NotionRecipesDB,
    Recipe,
)
from src.grocery_wizard.recipes.classify import classify_recipe
from src.grocery_wizard.recipes.scraper import ScrapeError, ingredients_to_text, scrape_recipe

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
    """Same rows as automatic ingredients backfill — edit Ingredients in Notion instead."""
    return recipe_missing_ingredients(recipe, schema)


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


def metadata_column_names(schema: DatabaseSchema) -> list[str]:
    """Filter columns (select / multi_select / status) — not checkboxes or Instructions."""
    return [col.name for col in schema.filter_columns]


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


def recipe_missing_metadata(recipe: Recipe, schema: DatabaseSchema) -> bool:
    """Link + populated ingredients, with at least one empty filter/metadata select column."""
    if not recipe_has_link(recipe):
        return False
    if not ingredients_text(recipe):
        return False
    for col in schema.filter_columns:
        current = recipe.properties.get(col.name)
        if is_blank_metadata_value(col.type, current):
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
) -> NotionFieldValues:
    updates: NotionFieldValues = {}
    for col in schema.filter_columns:
        if col.name not in inferred:
            continue
        current = recipe.properties.get(col.name)
        if not is_blank_metadata_value(col.type, current):
            continue
        value = inferred[col.name]
        if value is None or value in ("", []):
            continue
        updates[col.name] = value
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
    return _blank_metadata_updates(recipe, schema, inferred)


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

        updates = infer_metadata_field_values(db, recipe, nyt_client=nyt_client)
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
