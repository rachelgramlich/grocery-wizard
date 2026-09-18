"""Flow 2: Build a merged grocery list from planned recipes.

Grocery list pipeline (dev/debug failure points):

1. **Per-recipe Notion lines** → ``expand_ingredient_line`` / normalize → ``collected``
2. **Aggregate + format** → base ``grocery_items`` (amount merge, pantry exclusion)
3. **Session merges** → re-add pantry, recurring template, extras, run removals, user edits
4. **Sort** → ``sort_grocery_items`` → final export list

``item_provenance`` is captured during step 1. After step 3-4, call
``align_item_provenance_with_items`` so dev "item sources" matches what ships.
"""

from __future__ import annotations

__all__ = [
    "NameLinkMismatch",
    "align_item_provenance_with_items",
    "build_grocery_list",
    "detect_name_link_mismatch",
    "format_grocery_item",
    "format_grocery_items_copy_text",
    "format_item_provenance",
    "format_meals_and_grocery_list",
    "format_meals_copy_text",
    "format_name_link_mismatch_warning",
    "merge_grocery_items",
    "normalize_grocery_list_item",
    "recipe_title_from_url",
]

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from src.grocery_wizard.ingredients.normalize import (
    aggregate_amounts,
    expand_ingredient_line,
    normalize_ingredient,
    parse_amount,
    should_show_amount,
)
from src.grocery_wizard.ingredients.parsed import (
    format_garlic_grocery_amount,
    format_lemon_zest_grocery_line,
)
from src.grocery_wizard.ingredients.sync import parse_ingredients_text
from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe, recipe_lookup_key
from src.grocery_wizard.shopping.line_items import strip_checklist_prefix, strip_line_item
from src.grocery_wizard.shopping.pantry import is_pantry_item, load_pantry
from src.grocery_wizard.shopping.recurring_weekly_items import prompt_recurring_weekly_items
from src.grocery_wizard.shopping.store_aisles import (
    ingredient_name,
    sort_grocery_items,
)

_NAME_LINK_MATCH_THRESHOLD = 0.85
_NYT_SLUG_ID_PREFIX = re.compile(r"^\d+-")

_COLOR_ONION_RE = re.compile(r"^(?:red|yellow|white|sweet)\s+onions?$", re.IGNORECASE)
_ONION_OR_ALTERNATIVE_DISPLAY = "red or yellow onions"


def _grocery_collection_key(display_name: str) -> str:
    """Canonical dedupe key; merges color onion variants with OR-alternative lines."""
    lowered = display_name.strip().lower()
    if lowered == _ONION_OR_ALTERNATIVE_DISPLAY.lower():
        return lowered
    if _COLOR_ONION_RE.match(lowered):
        return _ONION_OR_ALTERNATIVE_DISPLAY.lower()
    return lowered


def _prefer_onion_display_name(existing: str, incoming: str) -> str:
    if " or " in incoming.lower():
        return incoming
    if " or " in existing.lower():
        return existing
    return incoming if len(incoming.split()) >= len(existing.split()) else existing


_TITLE_NORMALIZE = re.compile(r"[^a-z0-9\s]+")


@dataclass(frozen=True)
class NameLinkMismatch:
    """Notion recipe Name does not match the title implied by Link."""

    recipe_name: str
    link: str
    link_title: str


def recipe_title_from_url(url: str) -> str | None:
    """Extract a human-readable recipe title from a URL slug."""
    slug = url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    slug = slug.split("?")[0]
    slug = _NYT_SLUG_ID_PREFIX.sub("", slug)
    if not slug or slug.startswith("http"):
        return None
    return slug.replace("-", " ").replace("_", " ").strip()


def _normalize_recipe_title(title: str) -> str:
    normalized = _TITLE_NORMALIZE.sub(" ", title.lower())
    return " ".join(normalized.split())


def detect_name_link_mismatch(recipe: Recipe) -> NameLinkMismatch | None:
    """Return a mismatch when Notion Name and Link slug title disagree."""
    if not recipe.link or not recipe.name:
        return None

    link_title = recipe_title_from_url(recipe.link)
    if not link_title:
        return None

    name_norm = _normalize_recipe_title(recipe.name)
    link_norm = _normalize_recipe_title(link_title)
    if name_norm == link_norm:
        return None

    ratio = difflib.SequenceMatcher(None, name_norm, link_norm).ratio()
    if ratio >= _NAME_LINK_MATCH_THRESHOLD:
        return None

    return NameLinkMismatch(
        recipe_name=recipe.name,
        link=recipe.link,
        link_title=link_title.title(),
    )


def format_name_link_mismatch_warning(mismatch: NameLinkMismatch) -> str:
    return (
        f"Name/link mismatch for '{mismatch.recipe_name}': "
        f"Link points to '{mismatch.link_title}' ({mismatch.link}). "
        "Ingredients may be stale — verify Notion Name, Link, and Ingredients match."
    )


def _provenance_display_item(item: str) -> str:
    """Strip bullet/checkbox prefixes from a provenance item key for display."""
    return strip_line_item(item) or item


def format_item_provenance(item_provenance: dict[str, list[str]]) -> str:
    """Format grocery-item → recipe mapping for display."""
    if not item_provenance:
        return ""

    lines = ["Item sources"]
    for item in sort_grocery_items(list(item_provenance)):
        recipes = item_provenance[item]
        display_item = _provenance_display_item(item)
        lines.append(f"- {display_item}: {', '.join(recipes)}")
    return "\n".join(lines)


def align_item_provenance_with_items(
    item_provenance: dict[str, list[str]],
    grocery_items: list[str],
) -> dict[str, list[str]]:
    """Map provenance onto the final grocery list lines (post-merge / post-edit)."""
    if not item_provenance or not grocery_items:
        return {}

    by_key: dict[str, list[str]] = {}
    for item, recipes in item_provenance.items():
        by_key[_normalized_item_key(item)] = recipes

    aligned: dict[str, list[str]] = {}
    for line in grocery_items:
        recipes = by_key.get(_normalized_item_key(line))
        if recipes:
            aligned[line] = recipes
    return aligned


def build_grocery_list(
    db: NotionRecipesDB,
    *,
    recipe_names: list[str],
    recipes: list[Recipe] | None = None,
    staples: list[str] | None = None,
    pantry_path: Path | None = None,
    pantry_extra: set[str] | None = None,
    recurring_weekly_items_path: Path | None = None,
    recurring_weekly_items: list[str] | None = None,
    include_recurring_weekly_items: bool = False,
    exclude_pantry: bool = True,
    ingredient_overrides: dict[str, str] | None = None,
) -> tuple[list[str], list[str], None, list[str], dict[str, list[str]], list[NameLinkMismatch]]:
    """Build grocery list items, excluded pantry items, and skipped recipe names (for UI use).

    Reads ingredients exclusively from Notion — never scrapes. Recipes whose
    Notion Ingredients field is empty are collected in the returned
    ``missing_ingredients`` list so callers can surface a backfill hint.

    Also returns ``item_provenance`` (grocery item → source recipe names) and
    ``name_link_mismatches`` when Notion Name and Link disagree.

    When ``ingredient_overrides`` is provided it maps recipe name (lowercase) to
    edited ingredient text that supersedes whatever is stored in Notion.

    ``recurring_weekly_items`` is a per-run override list (flow A). It does not
    read or write the on-disk recurring template; callers pass the merged list
    for this session only.

    When ``recipes`` is provided, it is used instead of calling ``db.query_recipes()``.
    """
    recipe_list = recipes if recipes is not None else db.query_recipes()
    recipes_by_name = {recipe_lookup_key(recipe.name): recipe for recipe in recipe_list}
    pantry = load_pantry(pantry_path)
    if pantry_extra:
        pantry = pantry | {item.strip().lower() for item in pantry_extra if item.strip()}

    # collected maps normalized_name_lower → (display_name, [amounts])
    collected: dict[str, tuple[str, list[str | None]]] = {}
    excluded_pantry: list[str] = []
    missing_ingredients: list[str] = []
    provenance: dict[str, set[str]] = {}
    name_link_mismatches: list[NameLinkMismatch] = []

    for name in recipe_names:
        lookup = recipe_lookup_key(name)
        recipe = recipes_by_name.get(lookup)
        override_text = (
            ingredient_overrides.get(lookup)
            if ingredient_overrides and lookup in ingredient_overrides
            else None
        )

        if recipe is None:
            ingredient_lines = (
                parse_ingredients_text(override_text)[0]
                if override_text and override_text.strip()
                else []
            )
            if not ingredient_lines:
                missing_ingredients.append(name)
                continue
            source_name = name.strip() or name
            for line in ingredient_lines:
                _collect_ingredient_line(
                    line,
                    pantry=pantry,
                    exclude_pantry=exclude_pantry,
                    collected=collected,
                    excluded_pantry=excluded_pantry,
                    recipe_name=source_name,
                    provenance=provenance,
                )
            continue

        mismatch = detect_name_link_mismatch(recipe)
        if mismatch:
            name_link_mismatches.append(mismatch)

        if override_text is not None:
            ingredient_lines = (
                parse_ingredients_text(override_text)[0] if override_text.strip() else []
            )
        else:
            ingredient_lines = _get_ingredient_lines(recipe)
        if not ingredient_lines:
            missing_ingredients.append(recipe.name)
            continue

        for line in ingredient_lines:
            _collect_ingredient_line(
                line,
                pantry=pantry,
                exclude_pantry=exclude_pantry,
                collected=collected,
                excluded_pantry=excluded_pantry,
                recipe_name=recipe.name,
                provenance=provenance,
            )

    seen: set[str] = set(collected.keys())
    grocery_items: list[str] = [
        format_grocery_item(display_name, aggregate_amounts(amounts, name=display_name))
        for display_name, amounts in collected.values()
    ]
    item_provenance = _build_item_provenance(collected, provenance)

    for staple in staples or []:
        _append_unique_items(grocery_items, seen, [staple])

    if include_recurring_weekly_items:
        recurring = (
            recurring_weekly_items
            if recurring_weekly_items is not None
            else prompt_recurring_weekly_items(
                path=recurring_weekly_items_path,
                interactive=False,
            )
        )
        _append_unique_items(grocery_items, seen, recurring)

    grocery_items = sort_grocery_items(grocery_items)
    excluded_pantry.sort(key=str.lower)
    return (
        grocery_items,
        excluded_pantry,
        None,
        missing_ingredients,
        item_provenance,
        name_link_mismatches,
    )


def _get_ingredient_lines(recipe: Recipe) -> list[str]:
    if recipe.ingredients and recipe.ingredients.strip():
        return parse_ingredients_text(recipe.ingredients)[0]
    return []


def _amount_for_grocery_display(name: str, amount: str | None) -> str | None:
    if amount is None:
        return None
    if name.lower() == "garlic" and amount.startswith(("clove:", "head:")):
        return format_garlic_grocery_amount(amount)
    return amount


def format_grocery_item(name: str, amount: str | None) -> str:
    """Format a grocery item for display: ``"amount name"`` or just ``name``."""
    if name.lower() == "lemons" and amount and amount.startswith("zest:"):
        return format_lemon_zest_grocery_line(amount)
    amount = _amount_for_grocery_display(name, amount)
    if amount is None:
        return name
    return f"{amount} {name}"


def normalize_grocery_list_item(item: str) -> str:
    """Normalize a raw grocery line for display, dedup, and aisle classification."""
    cleaned = strip_checklist_prefix(item)
    if not cleaned:
        return ""
    name, amount = parse_amount(cleaned)
    if not name:
        name = normalize_ingredient(cleaned) or cleaned.strip()
        amount = None
    else:
        name = normalize_ingredient(name) or name
    if name.lower() == "garlic" and amount is not None:
        amount = aggregate_amounts([amount], name=name) or amount
    return format_grocery_item(name, amount)


def merge_grocery_items(
    *item_lists: list[str],
    sort: bool = True,
) -> list[str]:
    """Merge grocery item lists, deduplicating on normalized keys."""
    merged: list[str] = []
    seen: set[str] = set()
    for items in item_lists:
        for raw in items:
            normalized = normalize_grocery_list_item(raw)
            if not normalized:
                continue
            key = _normalized_item_key(normalized)
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    if sort:
        merged = sort_grocery_items(merged)
    return merged


def format_meals_copy_text(meals: list[tuple[str, str | None]]) -> str:
    """Meals block for copy/export (bullets only — no section title line)."""
    lines: list[str] = []
    for name, link in meals:
        if link:
            lines.append(f"- {name} ({link})")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def format_grocery_items_copy_text(grocery_items: list[str]) -> str:
    """Grocery block for copy/export (bullets only — no section title line)."""
    sorted_items = merge_grocery_items(grocery_items)
    return "\n".join(f"- {item}" for item in sorted_items)


def format_meals_and_grocery_list(
    meals: list[tuple[str, str | None]],
    grocery_items: list[str],
) -> str:
    """Format meals and grocery items as a single copy/pasteable block."""
    meals_body = format_meals_copy_text(meals)
    grocery_body = format_grocery_items_copy_text(grocery_items)
    if meals_body and grocery_body:
        return f"Meals\n{meals_body}\n\nGrocery List\n{grocery_body}"
    if meals_body:
        return f"Meals\n{meals_body}\n\nGrocery List"
    if grocery_body:
        return f"Grocery List\n{grocery_body}"
    return "Grocery List"


def _normalized_item_key(name: str) -> str:
    cleaned = strip_checklist_prefix(name)
    return (normalize_ingredient(cleaned) or ingredient_name(cleaned) or cleaned.strip()).lower()


def _append_unique_items(
    grocery_items: list[str],
    seen: set[str],
    new_items: list[str],
) -> None:
    """Add items that are not already present on the list or in *seen*."""
    for item in new_items:
        normalized = normalize_grocery_list_item(item)
        if not normalized:
            continue
        key = _normalized_item_key(normalized)
        if key in seen or _item_already_present(key, grocery_items):
            continue
        seen.add(key)
        grocery_items.append(normalized)


def _item_already_present(key: str, grocery_items: list[str]) -> bool:
    return any(_normalized_item_key(existing) == key for existing in grocery_items)


def _collect_ingredient_line(
    line: str,
    *,
    pantry: set[str],
    exclude_pantry: bool,
    collected: dict[str, tuple[str, list[str | None]]],
    excluded_pantry: list[str],
    recipe_name: str | None = None,
    provenance: dict[str, set[str]] | None = None,
) -> None:
    """Parse *line*, deduplicate by normalised name, and accumulate amounts.

    Pantry items are routed to *excluded_pantry* instead of *collected*.
    Ingredient lines are expected to be pre-cleaned at Notion ingest time.
    """
    for part in expand_ingredient_line(line):
        _name, amount = parse_amount(part)
        display_name = normalize_ingredient(part) or _name
        if not display_name:
            continue
        keeps_amount = amount and not amount.startswith(("head:", "clove:", "zest:"))
        if keeps_amount and not should_show_amount(amount, part):
            amount = None
        if exclude_pantry and is_pantry_item(display_name, pantry):
            if display_name not in excluded_pantry:
                excluded_pantry.append(display_name)
            continue
        key = _grocery_collection_key(display_name)
        if key in collected:
            existing_name, amounts = collected[key]
            display_name = _prefer_onion_display_name(existing_name, display_name)
            amounts.append(amount)
            collected[key] = (display_name, amounts)
        else:
            collected[key] = (display_name, [amount])
        if recipe_name and provenance is not None:
            provenance.setdefault(key, set()).add(recipe_name)


def _build_item_provenance(
    collected: dict[str, tuple[str, list[str | None]]],
    provenance: dict[str, set[str]],
) -> dict[str, list[str]]:
    """Map formatted grocery items to the recipe names they came from."""
    item_provenance: dict[str, list[str]] = {}
    for key, (display_name, amounts) in collected.items():
        recipes = provenance.get(key)
        if not recipes:
            continue
        item = format_grocery_item(display_name, aggregate_amounts(amounts, name=display_name))
        item_provenance[item] = sorted(recipes)
    return item_provenance


def _split_ingredient_text(text: str) -> list[str]:
    """Deprecated: use parse_ingredients_text from sync instead."""
    return parse_ingredients_text(text)[0]
