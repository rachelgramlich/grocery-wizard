"""Tests for shared grocery wizard flow helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.ui.grocery_flow import (
    GroceryPreBuildOptions,
    clear_review_ingredient_widget_keys,
    default_pre_build_grocery_options,
    fetch_recipe_review_text,
    ingredient_overrides_from_review,
    persist_reviewed_ingredients_to_notion,
    stash_grocery_result,
    stash_recipe_review,
    sync_recipe_review_overrides_to_session,
)


def _recipe(name: str, *, ingredients: str = "1 cup flour") -> Recipe:
    return Recipe(
        page_id=name,
        name=name,
        link=None,
        ingredients=ingredients,
        properties={},
    )


def test_fetch_recipe_review_text_formats_notion_storage() -> None:
    stored = "clove:5 garlic"
    recipes = [_recipe("Soup", ingredients=stored)]
    review = fetch_recipe_review_text(["Soup"], recipes)
    assert "5 cloves garlic" in review["Soup"]
    assert "clove:5" not in review["Soup"]


def test_stash_recipe_review_uses_formatted_text(monkeypatch: pytest.MonkeyPatch) -> None:
    session: dict = {}
    recipes = [_recipe("Soup", ingredients="raw")]
    monkeypatch.setattr(
        "src.grocery_wizard.ui.grocery_flow.format_ingredients_for_review",
        lambda raw: f"formatted:{raw}",
    )
    opts = GroceryPreBuildOptions(
        exclude_pantry=True,
        recurring_text="banana",
        default_recurring=["banana"],
        extra_items_text="",
    )
    session["review_ing_0"] = "stale widget text"
    stash_recipe_review(session, ["Soup"], recipes, opts)
    assert session["grocery_per_recipe_review"]["Soup"] == "formatted:raw"
    assert session["grocery_review_baseline"]["Soup"] == "formatted:raw"
    assert session["grocery_review_recipes"] == recipes
    assert "review_ing_0" not in session


def test_sync_recipe_review_overrides_to_session_reads_widget_keys() -> None:
    session = {
        "grocery_per_recipe_review": {"Soup": "original"},
        "review_ing_0": "3 carrots\n",
    }
    synced = sync_recipe_review_overrides_to_session(session, ["Soup"])
    assert synced["Soup"] == "3 carrots\n"
    assert session["grocery_per_recipe_review"]["Soup"] == "3 carrots\n"
    assert ingredient_overrides_from_review(synced) == {"soup": "3 carrots\n"}


def test_persist_reviewed_ingredients_to_notion_updates_changed_recipes() -> None:
    db = MagicMock()
    db.schema.ingredients_column = "Ingredients"
    recipe = _recipe("Soup", ingredients="1 cup flour")
    review = {"Soup": "2 cups flour\n"}
    baseline = {"Soup": "1 cup flour\n"}

    updated = persist_reviewed_ingredients_to_notion(
        db,
        [recipe],
        baseline=baseline,
        review=review,
    )

    assert updated == ["Soup"]
    db.update_recipe.assert_called_once()
    page_id, fields = db.update_recipe.call_args[0]
    assert page_id == recipe.page_id
    assert "Ingredients" in fields


def test_persist_reviewed_ingredients_skips_unchanged() -> None:
    db = MagicMock()
    db.schema.ingredients_column = "Ingredients"
    recipe = _recipe("Soup")
    text = "1 cup flour\n"
    persist_reviewed_ingredients_to_notion(
        db,
        [recipe],
        baseline={"Soup": text},
        review={"Soup": text},
    )
    db.update_recipe.assert_not_called()


def test_clear_review_ingredient_widget_keys() -> None:
    session = {"review_ing_0": "a", "review_ing_1": "b", "other": 1}
    clear_review_ingredient_widget_keys(session)
    assert session == {"other": 1}


def test_stash_grocery_result_passes_review_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    session: dict = {}
    db = MagicMock()
    db.query_recipes.return_value = [_recipe("Soup")]
    build_mock = MagicMock(return_value=(["flour"], [], None, [], {}, []))
    monkeypatch.setattr(
        "src.grocery_wizard.ui.grocery_flow.build_grocery_list",
        build_mock,
    )
    opts = GroceryPreBuildOptions(
        exclude_pantry=True,
        recurring_text="",
        default_recurring=[],
        extra_items_text="flowers",
    )
    recipes = [_recipe("Soup")]
    review = {"Soup": "1 cup flour\n"}
    stash_grocery_result(session, db, ["Soup"], opts, recipes=recipes, review=review)
    build_mock.assert_called_once()
    _args, kwargs = build_mock.call_args
    assert kwargs["ingredient_overrides"] == {"soup": "1 cup flour\n"}
    assert kwargs["recipes"] == recipes
    assert session["grocery_result"]["additional_text"] == "flowers"


def test_default_pre_build_respects_session_recurring() -> None:
    session = {
        "grocery_session_recurring_additions": ["flowers"],
        "grocery_pre_extra_items_epoch": 0,
        "grocery_pre_extra_items_0": "extra line",
    }
    opts = default_pre_build_grocery_options(session)
    assert "flowers" in opts.default_recurring
    assert opts.extra_items_text == "extra line"
