"""Recipe title normalization when reading and writing Notion."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.grocery_wizard.integrations.notion import (
    ColumnInfo,
    DatabaseSchema,
    NotionRecipesDB,
    normalize_recipe_link,
    normalize_recipe_name,
)


def _schema() -> DatabaseSchema:
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        filter_columns=[],
        checkbox_columns=[],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
        },
    )


def test_normalize_recipe_name_strips_edges() -> None:
    assert normalize_recipe_name("  Pizza beans \xa0") == "Pizza beans"


def test_normalize_recipe_link_strips_tracking_params_and_www() -> None:
    url = "https://www.example.com/recipes/1-soup/?smid=share&cgs=c"
    assert normalize_recipe_link(url) == "https://example.com/recipes/1-soup"


def test_create_recipe_strips_name_before_write(monkeypatch) -> None:
    db = NotionRecipesDB.__new__(NotionRecipesDB)
    db.schema = _schema()
    db._database_id = "db"
    db._data_source_id = "ds-id"
    db._config = MagicMock(recipe_image_column=None)
    captured: dict = {}

    def fake_create(*, parent, properties):
        captured["parent"] = parent
        captured["properties"] = properties
        return {
            "id": "page-1",
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Pizza beans"}]},
                "Link": {"type": "url", "url": None},
                "Ingredients": {"type": "rich_text", "rich_text": []},
            },
        }

    db._client = MagicMock()
    db._client.pages.create.side_effect = fake_create
    db._page_to_recipe = NotionRecipesDB._page_to_recipe.__get__(db)  # type: ignore[method-assign]

    db.create_recipe(
        {
            "Name": "  Pizza beans  ",
            "Link": "https://www.example.com/pizza/?utm=1",
        }
    )

    assert captured["parent"] == {
        "type": "data_source_id",
        "data_source_id": "ds-id",
    }
    title_payload = captured["properties"]["Name"]["title"][0]["text"]["content"]
    assert title_payload == "Pizza beans"
    assert captured["properties"]["Link"]["url"] == "https://example.com/pizza"
