"""Tests for recipe maintenance backfill helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema, Recipe
from src.grocery_wizard.recipes.recipe_maintenance import (
    infer_metadata_field_values,
    is_blank_metadata_value,
    recipe_missing_ingredients,
    recipe_missing_metadata,
    recipes_missing_ingredients,
    recipes_missing_metadata,
    run_ingredients_backfill,
    run_metadata_backfill,
)
from src.grocery_wizard.recipes.scraper import ScrapedRecipe, ScrapeError


def _schema() -> DatabaseSchema:
    meal = ColumnInfo(name="Meal", type="select", options=["Dinner", "Dessert"])
    weeknight = ColumnInfo(name="Dinner: Weeknight Friendly", type="checkbox", options=[])
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        instructions_column="Instructions",
        filter_columns=[meal],
        checkbox_columns=[weeknight],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Instructions": ColumnInfo(name="Instructions", type="rich_text"),
            "Meal": meal,
            "Dinner: Weeknight Friendly": weeknight,
        },
    )


def _recipe(
    *,
    link: str = "https://example.com/r",
    ingredients: str = "",
    meal: str | None = None,
    weeknight: bool = False,
) -> Recipe:
    props = {
        "Meal": meal,
        "Dinner: Weeknight Friendly": weeknight,
        "Instructions": "",
    }
    return Recipe(
        page_id="page-1",
        name="Chicken Pasta",
        link=link,
        ingredients=ingredients,
        properties=props,
    )


def test_recipe_missing_ingredients_predicate() -> None:
    schema = _schema()
    assert recipe_missing_ingredients(_recipe(ingredients=""), schema)
    assert not recipe_missing_ingredients(_recipe(ingredients="1 cup rice"), schema)
    assert not recipe_missing_ingredients(_recipe(link="", ingredients=""), schema)


def test_recipe_missing_metadata_predicate() -> None:
    schema = _schema()
    assert recipe_missing_metadata(_recipe(ingredients="1 cup rice", meal=None), schema)
    assert not recipe_missing_metadata(
        _recipe(ingredients="1 cup rice", meal="Dinner", weeknight=False),
        schema,
    )
    assert not recipe_missing_metadata(_recipe(ingredients="", meal=None), schema)


def test_unchecked_checkbox_does_not_count_as_metadata_gap() -> None:
    schema = _schema()
    assert not recipe_missing_metadata(
        _recipe(ingredients="1 cup rice", meal="Dinner", weeknight=False),
        schema,
    )


def test_is_blank_metadata_value() -> None:
    assert is_blank_metadata_value("select", None)
    assert is_blank_metadata_value("multi_select", [])
    assert not is_blank_metadata_value("select", "Dinner")


def test_recipes_missing_lists() -> None:
    schema = _schema()
    recipes = [
        _recipe(ingredients=""),
        _recipe(ingredients="salt", meal="Dinner", weeknight=True),
        _recipe(ingredients="pepper", meal=None),
    ]
    assert len(recipes_missing_ingredients(recipes, schema)) == 1
    assert len(recipes_missing_metadata(recipes, schema)) == 1


def test_run_ingredients_backfill_updates_notion() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    candidate = _recipe(ingredients="")

    scraped = ScrapedRecipe(
        url=candidate.link or "",
        title="Chicken Pasta",
        ingredients=["1 lb chicken", "8 oz pasta"],
    )

    with (
        patch(
            "src.grocery_wizard.recipes.recipe_maintenance.scrape_recipe",
            return_value=scraped,
        ),
        patch(
            "src.grocery_wizard.recipes.recipe_maintenance.prepare_ingredients_for_notion",
            side_effect=lambda text, **_: text,
        ),
    ):
        summary = run_ingredients_backfill(db, [candidate])

    assert summary.succeeded == 1
    db.update_recipe.assert_called_once()
    args = db.update_recipe.call_args[0]
    assert args[0] == "page-1"
    assert "Ingredients" in args[1]


def test_run_ingredients_backfill_counts_scrape_errors() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    candidate = _recipe(ingredients="")

    with patch(
        "src.grocery_wizard.recipes.recipe_maintenance.scrape_recipe",
        side_effect=ScrapeError("blocked"),
    ):
        summary = run_ingredients_backfill(db, [candidate])

    assert summary.failed == 1
    db.update_recipe.assert_not_called()


def test_run_metadata_backfill_fills_blanks_only() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    candidate = _recipe(ingredients="1 lb chicken\n8 oz pasta", meal=None, weeknight=False)

    with patch(
        "src.grocery_wizard.recipes.recipe_maintenance.infer_metadata_field_values",
        return_value={"Meal": "Dinner"},
    ):
        summary = run_metadata_backfill(db, [candidate])

    assert summary.succeeded == 1
    db.update_recipe.assert_called_once_with("page-1", {"Meal": "Dinner"})


def test_infer_metadata_field_values_uses_classify() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    candidate = _recipe(ingredients="1 lb chicken breast", meal=None, weeknight=False)

    with patch(
        "src.grocery_wizard.recipes.recipe_maintenance._resolve_total_minutes",
        return_value=45.0,
    ):
        updates = infer_metadata_field_values(db, candidate, nyt_client=None)

    assert updates.get("Meal") == "Dinner"
    assert "Dinner: Weeknight Friendly" not in updates
