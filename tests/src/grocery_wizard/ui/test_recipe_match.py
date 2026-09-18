"""Tests for plan meal ↔ Notion recipe matching helpers."""

from __future__ import annotations

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.ui.recipe_match import (
    recipe_for_plan_name,
    unmatched_plan_recipe_names,
)


def _recipe(name: str) -> Recipe:
    return Recipe(page_id=name, name=name, link=None, ingredients="salt", properties={})


def test_unmatched_plan_recipe_names_flags_missing_notion_row() -> None:
    recipes = [_recipe("Soup")]
    assert unmatched_plan_recipe_names(["Soup", "Pizza beans"], recipes) == ["Pizza beans"]


def test_recipe_for_plan_name_matches_after_notion_name_strip() -> None:
    recipes = [_recipe("Pizza beans")]
    assert recipe_for_plan_name("Pizza beans", recipes) is not None
    assert recipe_for_plan_name("  Pizza beans ", recipes) is not None
