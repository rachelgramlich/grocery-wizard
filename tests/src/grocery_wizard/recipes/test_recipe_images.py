"""Notion Files column URL parsing."""

from __future__ import annotations

from src.grocery_wizard.recipes.recipe_images import read_files_property_url


def test_read_files_property_url_prefers_first_file() -> None:
    prop = {
        "type": "files",
        "files": [
            {
                "type": "file",
                "file": {"url": "https://prod-files-secure.s3.us-west-2.amazonaws.com/x.jpg"},
            }
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
