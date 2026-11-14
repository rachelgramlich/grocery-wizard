"""Notion Files column URL parsing and cover detection."""

from __future__ import annotations

from src.grocery_wizard.integrations.notion import DatabaseSchema, Recipe
from src.grocery_wizard.recipes.recipe_images import (
    files_property_has_attachment,
    read_files_property_names,
    read_files_property_url,
    recipe_has_cover_image,
)


def _schema() -> DatabaseSchema:
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column=None,
        filter_columns=[],
        checkbox_columns=[],
        all_columns={},
        image_column="Cover image",
    )


def test_read_files_property_url_prefers_first_file() -> None:
    prop = {
        "type": "files",
        "files": [
            {
                "type": "file",
                "file": {"url": "https://prod-files-secure.s3.us-west-2.amazonaws.com/x.jpg"},
            },
        ],
    }
    assert read_files_property_url(prop) == (
        "https://prod-files-secure.s3.us-west-2.amazonaws.com/x.jpg"
    )


def test_read_files_property_url_external() -> None:
    prop = {
        "type": "files",
        "files": [{"type": "external", "external": {"url": "https://example.com/cover.png"}}],
    }
    assert read_files_property_url(prop) == "https://example.com/cover.png"


def test_read_files_property_url_file_upload_without_url() -> None:
    prop = {
        "type": "files",
        "files": [
            {
                "type": "file_upload",
                "name": "cover.jpg",
                "file_upload": {"id": "upload-1"},
            },
        ],
    }
    assert read_files_property_url(prop) is None
    assert files_property_has_attachment(prop)
    assert read_files_property_names(prop) == ["cover.jpg"]


def test_recipe_has_cover_image_with_url_or_property_names() -> None:
    schema = _schema()
    url_only = Recipe(
        page_id="a",
        name="A",
        link=None,
        ingredients=None,
        properties={},
        image_file_url="https://example.com/x.png",
    )
    assert recipe_has_cover_image(url_only, schema)

    props_only = Recipe(
        page_id="b",
        name="B",
        link=None,
        ingredients=None,
        properties={"Cover image": ["file"]},
    )
    assert recipe_has_cover_image(props_only, schema)

    empty = Recipe(
        page_id="c",
        name="C",
        link=None,
        ingredients=None,
        properties={},
    )
    assert not recipe_has_cover_image(empty, schema)
