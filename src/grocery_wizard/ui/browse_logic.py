"""Filter, sort, and grid HTML for Browse recipes."""

from __future__ import annotations

import hashlib
import html
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.grocery_wizard.integrations.notion import (
    ColumnInfo,
    DatabaseSchema,
    NotionRecipesDB,
    Recipe,
)
from src.grocery_wizard.planning.meal_planner import (
    MealPlanFilters,
    default_filters,
    filter_recipes,
)
from src.grocery_wizard.recipes.recipe_images import recipe_has_cover_image
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    plan_selection_count,
    rejection_count_column_name,
    selection_count_column_name,
    suggestion_rejection_count,
)

BROWSE_PAGE_SIZE = 24
BROWSE_FILTER_KEY_PREFIX = "browse"

_SESSION_APPLIED = "browse_applied_filters"
_SESSION_SORT_SEED = "browse_sort_seed"
_SESSION_VISIBLE_COUNT = "browse_visible_count"
_SESSION_RESERVED_KEYS = frozenset(
    {_SESSION_APPLIED, _SESSION_SORT_SEED, _SESSION_VISIBLE_COUNT},
)


@dataclass
class BrowseAppliedFilters:
    """Last-applied browse filters (meal-plan filters + browse-only has-image)."""

    meal_filters: MealPlanFilters
    has_image: bool = True


def default_browse_applied(schema_columns: dict[str, ColumnInfo]) -> BrowseAppliedFilters:
    return BrowseAppliedFilters(meal_filters=default_filters(schema_columns), has_image=True)


def empty_browse_applied() -> BrowseAppliedFilters:
    return BrowseAppliedFilters(meal_filters=MealPlanFilters(), has_image=False)


def applied_to_dict(state: BrowseAppliedFilters) -> dict[str, Any]:
    return {
        "values": dict(state.meal_filters.values),
        "ingredient_names": list(state.meal_filters.ingredient_names),
        "ingredient_mode": state.meal_filters.ingredient_mode,
        "has_image": state.has_image,
    }


def applied_from_dict(raw: dict[str, Any] | None) -> BrowseAppliedFilters | None:
    if not raw or not isinstance(raw, dict):
        return None
    values = raw.get("values")
    if not isinstance(values, dict):
        values = {}
    ingredient_names = raw.get("ingredient_names")
    if not isinstance(ingredient_names, list):
        ingredient_names = []
    ingredient_mode = raw.get("ingredient_mode")
    if ingredient_mode not in ("include", "exclude"):
        ingredient_mode = "include"
    has_image = raw.get("has_image")
    if not isinstance(has_image, bool):
        has_image = True
    return BrowseAppliedFilters(
        meal_filters=MealPlanFilters(
            values=values,
            ingredient_names=[str(n) for n in ingredient_names if n],
            ingredient_mode=str(ingredient_mode),
        ),
        has_image=has_image,
    )


def clear_browse_widget_session_state(session_state: Any) -> None:
    """Remove draft filter widget keys so Reset leaves empty controls."""
    to_delete = [
        key
        for key in list(session_state.keys())
        if isinstance(key, str)
        and key.startswith(BROWSE_FILTER_KEY_PREFIX)
        and key not in _SESSION_RESERVED_KEYS
    ]
    for key in to_delete:
        del session_state[key]


def browse_session_applied_key() -> str:
    return _SESSION_APPLIED


def browse_session_sort_seed_key() -> str:
    return _SESSION_SORT_SEED


def browse_session_visible_count_key() -> str:
    return _SESSION_VISIBLE_COUNT


def browse_recipes_for_applied(
    recipes: list[Recipe],
    db: NotionRecipesDB,
    applied: BrowseAppliedFilters,
    *,
    ingredient_index: dict[str, set[str]] | None,
    sort_seed: int,
) -> list[Recipe]:
    """Filter and sort the recipe library for the browse grid."""
    schema_columns = db.schema.all_columns
    filtered = filter_recipes(
        recipes,
        applied.meal_filters,
        schema_columns,
        ingredient_index=ingredient_index,
    )
    if applied.has_image:
        schema = db.schema
        filtered = [recipe for recipe in filtered if recipe_has_cover_image(recipe, schema)]
    selection_column = selection_count_column_name(db)
    rejections_column = rejection_count_column_name(db)
    return sort_browse_recipes(
        filtered,
        sort_seed=sort_seed,
        selection_column=selection_column,
        rejections_column=rejections_column,
    )


def sort_browse_recipes(
    recipes: list[Recipe],
    *,
    sort_seed: int,
    selection_column: str | None,
    rejections_column: str | None,
) -> list[Recipe]:
    """Selection ↑, rejection ↑, last_edited_time ↑, seeded random tie-break."""

    def tie_break(recipe: Recipe) -> int:
        digest = hashlib.md5(f"{recipe.page_id}:{sort_seed}".encode(), usedforsecurity=False)
        return int.from_bytes(digest.digest()[:4], "big")

    def sort_key(recipe: Recipe) -> tuple[int, int, datetime, int]:
        selection = plan_selection_count(recipe, selection_column=selection_column)
        rejection = suggestion_rejection_count(recipe, rejections_column=rejections_column)
        edited = recipe.last_edited_time
        if edited is None:
            edited = datetime.min.replace(tzinfo=UTC)
        elif edited.tzinfo is None:
            edited = edited.replace(tzinfo=UTC)
        return (selection, rejection, edited, tie_break(recipe))

    return sorted(recipes, key=sort_key)


def render_browse_grid_html(
    recipes: list[Recipe],
    *,
    limit: int,
    schema: DatabaseSchema | None = None,
) -> str:
    """Build the Instagram-like card grid (V1: not clickable)."""
    visible = recipes[:limit]
    tiles: list[str] = []
    for recipe in visible:
        name = html.escape(recipe.name or "Untitled")
        url = recipe.image_file_url
        if url and url.startswith(("http://", "https://")):
            safe_url = html.escape(url, quote=True)
            image_block = (
                f'<img class="gw-browse-tile-img" src="{safe_url}" alt="" loading="lazy" />'
            )
        elif schema and recipe_has_cover_image(recipe, schema):
            image_block = (
                '<div class="gw-browse-tile-placeholder gw-browse-tile-not-loaded">'
                "<span>Photo in Notion</span></div>"
            )
        else:
            image_block = '<div class="gw-browse-tile-placeholder"><span>No photo</span></div>'
        tiles.append(
            f'<article class="gw-browse-tile" aria-label="{name}">'
            f'<div class="gw-browse-tile-media">{image_block}</div>'
            f'<p class="gw-browse-tile-title">{name}</p>'
            f"</article>"
        )
    if not tiles:
        return '<p class="gw-browse-empty">No recipes match these filters.</p>'
    return f'<div class="gw-browse-grid">{"".join(tiles)}</div>'


def new_browse_sort_seed() -> int:
    return random.randint(0, 2**31 - 1)
