"""Tests for recipe maintenance backfill helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema, Recipe
from src.grocery_wizard.recipes.recipe_maintenance import (
    _resolve_total_minutes,
    infer_metadata_field_values,
    is_blank_metadata_value,
    recipe_manual_ingredients_in_notion,
    recipe_missing_ingredients,
    recipe_missing_metadata,
    recipe_possibly_missing_all_checkboxes,
    recipes_missing_ingredients,
    recipes_missing_metadata,
    run_ingredients_backfill,
    run_metadata_backfill,
)
from src.grocery_wizard.recipes.scraper import ScrapedRecipe, ScrapeError


def _schema() -> DatabaseSchema:
    return _full_schema(filter_columns_only_meal=True)


def _full_schema(*, filter_columns_only_meal: bool = False) -> DatabaseSchema:
    meal = ColumnInfo(name="Meal", type="select", options=["Dinner", "Dessert", "Lunch"])
    weeknight = ColumnInfo(name="Dinner: Weeknight Friendly", type="checkbox", options=[])
    cuisine = ColumnInfo(name="Cuisine", type="multi_select", options=["Italian"])
    protein = ColumnInfo(name="Protein", type="multi_select", options=["Chicken"])
    dinner_category = ColumnInfo(
        name="Dinner Category",
        type="multi_select",
        options=["Pasta"],
    )
    filter_columns = [meal]
    if not filter_columns_only_meal:
        filter_columns = [meal, cuisine, protein, dinner_category]
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        instructions_column="Instructions",
        filter_columns=filter_columns,
        checkbox_columns=[weeknight],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Instructions": ColumnInfo(name="Instructions", type="rich_text"),
            "Meal": meal,
            "Cuisine": cuisine,
            "Protein": protein,
            "Dinner Category": dinner_category,
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


def test_recipe_manual_ingredients_requires_empty_link_and_ingredients() -> None:
    schema = _schema()
    assert recipe_manual_ingredients_in_notion(_recipe(link="", ingredients=""), schema)
    assert not recipe_manual_ingredients_in_notion(_recipe(ingredients=""), schema)
    assert not recipe_manual_ingredients_in_notion(_recipe(link="", ingredients="salt"), schema)


def test_recipe_possibly_missing_all_checkboxes() -> None:
    schema = _schema()
    assert recipe_possibly_missing_all_checkboxes(
        _recipe(ingredients="x", meal="Dinner", weeknight=False),
        schema,
    )
    assert not recipe_possibly_missing_all_checkboxes(
        _recipe(ingredients="x", meal="Dinner", weeknight=True),
        schema,
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
        _recipe(ingredients="1 cup rice", meal="Dinner", weeknight=True),
        schema,
    )
    assert not recipe_missing_metadata(_recipe(ingredients="", meal=None), schema)


def test_unchecked_weeknight_counts_as_gap_for_dinner() -> None:
    schema = _schema()
    assert recipe_missing_metadata(
        _recipe(ingredients="1 cup rice", meal="Dinner", weeknight=False),
        schema,
    )


def test_dessert_skips_protein_and_dinner_category_gaps() -> None:
    schema = _full_schema()
    props = {
        "Meal": "Dessert",
        "Cuisine": ["Italian"],
        "Protein": None,
        "Dinner Category": None,
        "Dinner: Weeknight Friendly": False,
    }
    recipe = Recipe(
        page_id="page-1",
        name="Brownies",
        link="https://example.com/r",
        ingredients="flour",
        properties=props,
    )
    assert not recipe_missing_metadata(recipe, schema)


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


def test_resolve_total_minutes_continues_when_scrape_blocked() -> None:
    with patch(
        "src.grocery_wizard.recipes.recipe_maintenance.scrape_recipe",
        side_effect=ScrapeError("Could not fetch recipe page: 403 Client Error"),
    ):
        minutes = _resolve_total_minutes("https://example.com/r", nyt_client=None)

    assert minutes is None


def test_run_metadata_backfill_continues_after_scrape_failure() -> None:
    schema = _schema()
    db = MagicMock()
    db.schema = schema
    candidate = _recipe(ingredients="1 lb chicken", meal=None)

    with patch(
        "src.grocery_wizard.recipes.recipe_maintenance.infer_metadata_field_values",
        side_effect=ScrapeError("Could not fetch recipe page: 403 Client Error"),
    ):
        summary = run_metadata_backfill(db, [candidate])

    assert summary.failed == 1
    db.update_recipe.assert_not_called()


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
    assert updates.get("Dinner: Weeknight Friendly") is True
