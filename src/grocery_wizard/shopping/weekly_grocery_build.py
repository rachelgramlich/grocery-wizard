"""Weekly grocery list build orchestration (domain; no Streamlit or ui imports)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.grocery_wizard.ingredients.sync import (
    format_ingredients_for_review,
    prepare_ingredients_for_notion,
)
from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe, recipe_lookup_key
from src.grocery_wizard.integrations.notion_list_logs import persist_list_log_to_notion
from src.grocery_wizard.shopping.grocery_list import build_grocery_list
from src.grocery_wizard.shopping.grocery_list_edits import compute_grocery_drafts
from src.grocery_wizard.shopping.line_items import parse_line_items
from src.grocery_wizard.shopping.list_log import (
    ListTrace,
    apply_adjustments,
    build_list_log,
    rewrite_list_log,
    write_list_log,
)


@dataclass(frozen=True)
class GroceryPreBuildOptions:
    exclude_pantry: bool
    recurring_text: str
    default_recurring: list[str]
    extra_items_text: str


def persist_single_recipe_review_to_notion(
    db: NotionRecipesDB,
    *,
    name: str,
    overrides: dict[str, str],
    recipes: list[Recipe],
    baseline_review: dict[str, str],
) -> bool:
    """Persist one recipe when review text differs from baseline.

    Returns True if Notion was updated.
    """
    updated = persist_reviewed_ingredients_to_notion(
        db,
        selected=[name],
        overrides=overrides,
        recipes=recipes,
        baseline_review=baseline_review,
    )
    return updated > 0


def persist_reviewed_ingredients_to_notion(
    db: NotionRecipesDB,
    *,
    selected: list[str],
    overrides: dict[str, str],
    recipes: list[Recipe],
    baseline_review: dict[str, str],
) -> int:
    """Write edited review text back to Notion for recipes that changed. Returns update count."""
    schema = db.schema
    ingredients_column = schema.ingredients_column
    if not ingredients_column:
        return 0

    recipes_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in recipes}
    updated = 0
    for name in selected:
        recipe = recipes_by_name.get(recipe_lookup_key(name))
        if recipe is None:
            continue
        edited = overrides.get(recipe_lookup_key(name), "")
        if edited.strip() == baseline_review.get(name, "").strip():
            continue
        prepared = prepare_ingredients_for_notion(edited, source_url=recipe.link)
        db.update_recipe(recipe.page_id, {ingredients_column: prepared})
        updated += 1
    return updated


def fetch_recipe_review_text(selected: list[str], recipes: list[Recipe]) -> dict[str, str]:
    recipes_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in recipes}
    review: dict[str, str] = {}
    for name in selected:
        recipe = recipes_by_name.get(recipe_lookup_key(name))
        raw = recipe.ingredients or "" if recipe else ""
        review[name] = format_ingredients_for_review(raw)
    return review


def ingredient_overrides_from_review(review: dict[str, str]) -> dict[str, str]:
    return {recipe_lookup_key(name): text for name, text in review.items()}


def build_grocery_result_payload(
    db: NotionRecipesDB,
    selected: list[str],
    *,
    exclude_pantry: bool,
    recurring_text: str,
    extra_items_text: str,
    pantry_extra: set[str],
    ingredient_overrides: dict[str, str] | None,
    pantry_names: set[str],
    recipes: list[Recipe] | None = None,
) -> dict[str, Any]:
    recurring_weekly_items = parse_line_items(recurring_text)
    trace = ListTrace()
    items, excluded, _sync_summary, missing_ingredients, item_provenance, mismatches = (
        build_grocery_list(
            db,
            recipe_names=selected,
            recipes=recipes,
            exclude_pantry=exclude_pantry,
            pantry_extra=pantry_extra,
            recurring_weekly_items=recurring_weekly_items,
            include_recurring_weekly_items=True,
            ingredient_overrides=ingredient_overrides,
            pantry_names=pantry_names,
            trace=trace,
        )
    )
    debug_log, debug_log_path, debug_log_notion_page_id, debug_log_notion_url = (
        _save_list_debug_log(
            trace,
            selected=selected,
            exclude_pantry=exclude_pantry,
            items=items,
            excluded=excluded,
            missing_ingredients=missing_ingredients,
            item_provenance=item_provenance,
            recurring_items=recurring_weekly_items,
            extra_items_text=extra_items_text,
        )
    )
    return {
        "debug_log": debug_log,
        "debug_log_path": debug_log_path,
        "debug_log_notion_page_id": debug_log_notion_page_id,
        "debug_log_notion_url": debug_log_notion_url,
        "items": items,
        "excluded": excluded,
        "missing_ingredients": missing_ingredients,
        "item_provenance": item_provenance,
        "name_link_mismatches": mismatches,
        "readd": [],
        "additional_text": extra_items_text,
        "recurring_items": list(recurring_weekly_items),
        "run_removals": [],
        "source_recipes": tuple(selected),
        "week_plan": tuple(selected),
    }


def _save_list_debug_log(
    trace: ListTrace,
    *,
    selected: list[str],
    exclude_pantry: bool,
    items: list[str],
    excluded: list[str],
    missing_ingredients: list[str],
    item_provenance: dict[str, list[str]],
    recurring_items: list[str],
    extra_items_text: str,
) -> tuple[dict[str, Any], str | None, str | None, str | None]:
    _, final_items = compute_grocery_drafts(
        items, [], extra_items_text, recurring_items=recurring_items
    )
    log = build_list_log(
        trace,
        meals=selected,
        exclude_pantry=exclude_pantry,
        excluded_pantry=excluded,
        missing_ingredients=missing_ingredients,
        item_provenance=item_provenance,
        extra_items=parse_line_items(extra_items_text),
        final_items=final_items,
    )
    path = write_list_log(log)
    page_id, url = persist_list_log_to_notion(log)
    return log, str(path) if path else None, page_id, url


def sync_list_debug_log_adjustments(
    result: dict[str, Any],
    *,
    final_items: list[str],
    readd: list[str],
    removed_once: list[str],
) -> None:
    """Keep the saved debug log in step with "Adjust this week's list" choices."""
    log = result.get("debug_log")
    path = result.get("debug_log_path")
    page_id = result.get("debug_log_notion_page_id")
    if not log:
        return
    adjustments = {"pantry_readded": list(readd), "removed_once": list(removed_once)}
    if log.get("user_adjustments") == adjustments:
        return
    updated = apply_adjustments(
        log, final_items=final_items, readd=readd, removed_once=removed_once
    )
    result["debug_log"] = updated
    if path:
        rewrite_list_log(Path(path), updated)
    if page_id:
        _, url = persist_list_log_to_notion(updated, page_id=page_id)
        if url:
            result["debug_log_notion_url"] = url
