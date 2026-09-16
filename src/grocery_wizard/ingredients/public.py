"""Stable entry points for ingredient pipelines.

Import from here when you are unsure whether to use ``parsed`` (storage) or
``normalize`` (grocery list). See ``ARCHITECTURE.md`` for the full diagram.
"""

from __future__ import annotations

__all__ = [
    "aggregate_amounts",
    "drop_junk_ingredient_lines",
    "format_ingredient_for_storage",
    "merge_ingredients",
    "minimal_clean_for_storage",
    "name_from_stored_line",
    "normalize_ingredient",
    "parse_amount",
    "parse_ingredients_text",
    "parse_stored_ingredient",
    "prepare_ingredients_for_notion",
    "should_show_amount",
]

from src.grocery_wizard.ingredients.normalize import (
    aggregate_amounts,
    drop_junk_ingredient_lines,
    normalize_ingredient,
    parse_amount,
    should_show_amount,
)
from src.grocery_wizard.ingredients.parsed import (
    format_ingredient_for_storage,
    minimal_clean_for_storage,
    name_from_stored_line,
    parse_stored_ingredient,
)
from src.grocery_wizard.ingredients.sync import (
    merge_ingredients,
    parse_ingredients_text,
    prepare_ingredients_for_notion,
)
