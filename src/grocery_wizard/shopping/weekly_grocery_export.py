"""Full weekly grocery list export (matches Streamlit build + merge + copy)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe, recipe_lookup_key
from src.grocery_wizard.shopping.grocery_list import format_grocery_items_copy_text
from src.grocery_wizard.ui.grocery_flow import (
    build_grocery_result_payload,
    fetch_recipe_review_text,
    ingredient_overrides_from_review,
)
from src.grocery_wizard.ui.grocery_helpers import compute_grocery_drafts


def recipes_from_week_dict(week: dict[str, Any]) -> list[Recipe]:
    return [
        Recipe(
            page_id=str(row["name"]),
            name=str(row["name"]),
            link=row.get("link"),
            ingredients=str(row["ingredients"]),
            properties={},
        )
        for row in week["recipes"]
    ]


def export_grocery_lines_for_week_dict(week: dict[str, Any]) -> list[str]:
    """Run review → build → merge extras/recurring → export lines (no bullets)."""
    names = [str(row["name"]) for row in week["recipes"]]
    recipes = recipes_from_week_dict(week)
    db = MagicMock()
    db.query_recipes.return_value = recipes

    review = fetch_recipe_review_text(names, recipes)
    pantry_names = {
        str(item).strip().lower() for item in week.get("pantry", []) if str(item).strip()
    }
    recurring = week.get("recurring") or []
    extra_items = str(week.get("extra_items") or "")

    payload = build_grocery_result_payload(
        db,
        names,
        exclude_pantry=bool(week.get("exclude_pantry", True)),
        recurring_text="\n".join(recurring),
        extra_items_text=extra_items,
        pantry_extra=set(),
        ingredient_overrides=ingredient_overrides_from_review(review),
        recipes=recipes,
        pantry_names=pantry_names,
    )
    _, final_items = compute_grocery_drafts(
        payload["items"],
        payload.get("readd") or [],
        payload.get("additional_text") or "",
        recurring_items=payload.get("recurring_items"),
    )
    copy_text = format_grocery_items_copy_text(final_items)
    return [line[2:].strip() for line in copy_text.splitlines() if line.strip()]


def export_grocery_lines_for_meal_plan(
    db: NotionRecipesDB,
    recipe_names: list[str],
    *,
    pantry_names: set[str] | None = None,
    recurring: list[str] | None = None,
    extra_items: str = "",
    exclude_pantry: bool = True,
) -> list[str]:
    """Build export lines from live Notion recipes (for export-golden-week)."""
    recipes_by_key = {recipe_lookup_key(r.name): r for r in db.query_recipes()}
    rows = []
    for name in recipe_names:
        recipe = recipes_by_key.get(recipe_lookup_key(name))
        if recipe is None:
            raise ValueError(f"Recipe not found: {name!r}")
        rows.append(
            {
                "name": recipe.name,
                "link": recipe.link,
                "ingredients": recipe.ingredients or "",
            }
        )
    week = {
        "recipes": rows,
        "pantry": sorted(pantry_names or []),
        "recurring": list(recurring or []),
        "extra_items": extra_items,
        "exclude_pantry": exclude_pantry,
    }
    return export_grocery_lines_for_week_dict(week)
