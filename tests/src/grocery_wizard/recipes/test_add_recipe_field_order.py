"""Add-recipe review field ordering (name, link, ingredients, instructions, metadata)."""

from __future__ import annotations

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.recipes.add_recipe import (
    base_recipe_field_values,
    ordered_recipe_field_names,
)


def _schema(*, instructions: bool = True) -> DatabaseSchema:
    all_columns = {
        "Name": ColumnInfo(name="Name", type="title"),
        "Link": ColumnInfo(name="Link", type="url"),
        "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
        "Meal": ColumnInfo(name="Meal", type="select", options=["Dinner"]),
    }
    if instructions:
        all_columns["Instructions"] = ColumnInfo(name="Instructions", type="rich_text")
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        instructions_column="Instructions" if instructions else None,
        filter_columns=[all_columns["Meal"]],
        checkbox_columns=[],
        all_columns=all_columns,
    )


def test_ordered_recipe_field_names_includes_instructions_after_ingredients() -> None:
    schema = _schema()
    assert ordered_recipe_field_names(schema) == [
        "Name",
        "Link",
        "Ingredients",
        "Instructions",
        "Meal",
    ]


def test_base_recipe_field_values_seeds_empty_instructions() -> None:
    schema = _schema()
    fields = base_recipe_field_values(schema)
    assert fields["Instructions"] == ""
