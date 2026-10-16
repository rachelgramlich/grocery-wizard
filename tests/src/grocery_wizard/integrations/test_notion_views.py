"""Notion view helpers for Recipe maintenance."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
from src.grocery_wizard.integrations.notion_views import (
    clear_notion_view_url_cache,
    ensure_notion_filtered_view_url,
    manual_ingredients_notion_filter,
    possibly_missing_checkboxes_notion_filter,
)


@pytest.fixture(autouse=True)
def _fresh_view_cache() -> None:
    clear_notion_view_url_cache()


def _schema() -> DatabaseSchema:
    meal = ColumnInfo(name="Meal", type="select", options=["Dinner"])
    weeknight = ColumnInfo(name="Dinner: Weeknight Friendly", type="checkbox", options=[])
    nyt = ColumnInfo(name="Synced from NYT recipe box", type="checkbox", options=[])
    return DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        instructions_column=None,
        filter_columns=[meal],
        checkbox_columns=[weeknight, nyt],
        all_columns={
            "Name": ColumnInfo(name="Name", type="title"),
            "Link": ColumnInfo(name="Link", type="url"),
            "Ingredients": ColumnInfo(name="Ingredients", type="rich_text"),
            "Meal": meal,
            "Dinner: Weeknight Friendly": weeknight,
            "Synced from NYT recipe box": nyt,
        },
    )


def test_manual_ingredients_notion_filter() -> None:
    filt = manual_ingredients_notion_filter(_schema())
    assert filt == {
        "and": [
            {"property": "Link", "url": {"is_empty": True}},
            {"property": "Ingredients", "rich_text": {"is_empty": True}},
        ],
    }


def test_possibly_missing_checkboxes_notion_filter() -> None:
    filt = possibly_missing_checkboxes_notion_filter(_schema())
    assert filt == {
        "and": [
            {"property": "Dinner: Weeknight Friendly", "checkbox": {"equals": False}},
            {"property": "Synced from NYT recipe box", "checkbox": {"equals": False}},
        ],
    }


def test_ensure_notion_filtered_view_url_reuses_named_view() -> None:
    db = MagicMock()
    db._database_id = "db-id"
    db._data_source_id = "ds-id"
    db.schema = _schema()
    client = MagicMock()
    db._client = client
    client.views.list.return_value = {"results": [{"id": "view-1"}]}
    client.views.retrieve.return_value = {"id": "view-1", "name": "My view"}
    client.views.update.return_value = {"url": "https://app.notion.com/p/example?v=view-1"}

    url = ensure_notion_filtered_view_url(
        db,
        view_name="My view",
        filter_obj={"property": "Link", "url": {"is_empty": True}},
    )

    assert url == "https://app.notion.com/p/example?v=view-1"
    client.views.create.assert_not_called()


def _db_with_client(client: MagicMock) -> MagicMock:
    db = MagicMock()
    db._database_id = "db-id"
    db._data_source_id = "ds-id"
    db.schema = _schema()
    db._client = client
    return db


def test_ensure_view_url_is_remembered_so_rerenders_make_no_requests() -> None:
    client = MagicMock()
    client.views.list.return_value = {"results": [{"id": "view-1"}]}
    client.views.retrieve.return_value = {"id": "view-1", "name": "My view"}
    client.views.update.return_value = {"url": "https://example/v1"}
    db = _db_with_client(client)
    filt = {"property": "Link", "url": {"is_empty": True}}

    first = ensure_notion_filtered_view_url(db, view_name="My view", filter_obj=filt)
    calls_after_first = len(client.method_calls)
    second = ensure_notion_filtered_view_url(db, view_name="My view", filter_obj=filt)

    assert first == second == "https://example/v1"
    assert len(client.method_calls) == calls_after_first


def test_two_views_in_one_database_share_a_single_view_listing() -> None:
    client = MagicMock()
    client.views.list.return_value = {"results": [{"id": "view-1"}]}
    client.views.retrieve.return_value = {"id": "view-1", "name": "Other"}
    client.views.create.side_effect = [
        {"id": "a", "url": "https://example/a"},
        {"id": "b", "url": "https://example/b"},
    ]
    db = _db_with_client(client)

    ensure_notion_filtered_view_url(db, view_name="A", filter_obj={"x": 1})
    ensure_notion_filtered_view_url(db, view_name="B", filter_obj={"x": 2})

    client.views.list.assert_called_once()
    client.views.retrieve.assert_called_once()


def test_clear_view_cache_forces_a_fresh_lookup() -> None:
    client = MagicMock()
    client.views.list.return_value = {"results": []}
    client.views.create.return_value = {"id": "a", "url": "https://example/a"}
    db = _db_with_client(client)

    ensure_notion_filtered_view_url(db, view_name="A", filter_obj={"x": 1})
    clear_notion_view_url_cache()
    ensure_notion_filtered_view_url(db, view_name="A", filter_obj={"x": 1})

    assert client.views.list.call_count == 2
