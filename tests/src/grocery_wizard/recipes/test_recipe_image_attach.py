"""Tests for best-effort recipe cover attach on create."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.recipes.add_recipe import add_prefetched_recipes
from src.grocery_wizard.recipes.recipe_image_attach import (
    NO_COVER_IMAGE_USER_MESSAGE,
    RecipeImageAttachResult,
    attach_recipe_cover_image,
)


def _db_with_image_column() -> MagicMock:
    db = MagicMock()
    db.schema = DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        image_column="Cover image",
        filter_columns=[],
        checkbox_columns=[],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Cover image": ColumnInfo(name="Cover image", type="files"),
        },
    )
    db.create_recipe.return_value = MagicMock(page_id="page-1", name="Soup")
    return db


def test_attach_recipe_cover_image_failure_returns_message() -> None:
    from src.grocery_wizard.recipes.recipe_image_resolver import ImageResolveError

    db = _db_with_image_column()
    with patch(
        "src.grocery_wizard.recipes.recipe_image_attach.resolve_recipe_image_url",
        side_effect=ImageResolveError("no og"),
    ):
        result = attach_recipe_cover_image(db, "page-1", "https://example.com/x")
    assert result.user_message == NO_COVER_IMAGE_USER_MESSAGE
    db.upload_recipe_image_file.assert_not_called()


def test_add_prefetched_still_creates_when_image_fails() -> None:
    db = _db_with_image_column()
    db.find_by_link.return_value = None
    with patch(
        "src.grocery_wizard.recipes.add_recipe.attach_recipe_cover_image",
        return_value=RecipeImageAttachResult(ok=False, user_message=NO_COVER_IMAGE_USER_MESSAGE),
    ):
        created = add_prefetched_recipes(
            db,
            [("Soup", "https://cooking.nytimes.com/recipes/1", ["salt"], 30.0)],
            no_confirm=True,
            include_ingredients=True,
        )
    assert len(created) == 1
    db.create_recipe.assert_called_once()
