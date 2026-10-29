"""Tests for Notion stored-ingredient reformat (no scrape)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.recipes.reformat_stored_ingredients import (
    ReformatStatus,
    analyze_stored_ingredient_reformat,
    recipes_linked_with_ingredients,
    run_stored_ingredients_reformat,
)
from tests.src.grocery_wizard.recipes.test_recipe_maintenance import _schema


def _recipe(*, link: str = "https://example.com/r", ingredients: str = "salt") -> Recipe:
    return Recipe(
        page_id="page-1",
        name="Test Recipe",
        link=link,
        ingredients=ingredients,
        properties={},
    )


def test_recipes_linked_with_ingredients_filters() -> None:
    schema = _schema()
    recipes = [
        _recipe(link="", ingredients="salt"),
        _recipe(ingredients=""),
        _recipe(ingredients="pepper"),
    ]
    assert len(recipes_linked_with_ingredients(recipes, schema)) == 1


def test_analyze_unchanged_when_already_formatted() -> None:
    text = "2 cans beans\nsliced cheese"
    analysis = analyze_stored_ingredient_reformat(text)
    assert analysis.status == ReformatStatus.UNCHANGED


def test_analyze_apply_ok_paren_ounce_can() -> None:
    analysis = analyze_stored_ingredient_reformat("2 (15-ounce) cans beans")
    assert analysis.status == ReformatStatus.APPLY_OK
    assert analysis.after == "2 cans beans"


def test_analyze_apply_ok_mushroom_or_continuation_line() -> None:
    before = (
        "3/4 pound mixed fresh mushrooms, such as shiitake\n"
        "cremini, thinly sliced, or whole shimeji mushrooms\n"
        "Kosher salt"
    )
    analysis = analyze_stored_ingredient_reformat(before)
    assert analysis.status == ReformatStatus.APPLY_OK
    assert "shimeji" in analysis.after.lower()


def test_analyze_apply_ok_when_line_count_drops_from_intentional_cleanup() -> None:
    before = (
        "Kosher salt\n"
        "and black pepper\n"
        "1/2 teaspoon finely grated lemon zest (from 1/2 lemon)\n"
        "1 can chickpeas"
    )
    analysis = analyze_stored_ingredient_reformat(before)
    assert analysis.status == ReformatStatus.APPLY_OK
    assert analysis.before_ingredient_line_count > analysis.after_ingredient_line_count
    assert "1 can chickpeas" in analysis.after


def test_run_dry_run_does_not_update_notion() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    recipe = _recipe(ingredients="2 (15-ounce) cans beans")
    run_stored_ingredients_reformat(db, [recipe], dry_run=True)
    db.update_recipe.assert_not_called()


def test_run_apply_updates_when_ok() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    recipe = _recipe(ingredients="2 (15-ounce) cans beans")
    analysis = analyze_stored_ingredient_reformat(recipe.ingredients or "")
    assert analysis.status == ReformatStatus.APPLY_OK
    summary = run_stored_ingredients_reformat(db, [recipe], dry_run=False)
    assert summary.updated == 1
    db.update_recipe.assert_called_once()
