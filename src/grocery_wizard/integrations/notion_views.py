"""Notion database views used by the Streamlit UI."""

from __future__ import annotations

from typing import Any

from src.grocery_wizard.integrations.notion import DatabaseSchema, NotionRecipesDB

_MANUAL_BACKFILL_VIEW_NAME = "Grocery Wizard — manual backfill"


def manual_backfill_notion_filter(schema: DatabaseSchema) -> dict[str, Any]:
    """Filter: Link empty AND Ingredients empty (manual entry in Notion)."""
    link_column = schema.link_column
    ingredients_column = schema.ingredients_column
    if not ingredients_column:
        return {"property": link_column, "url": {"is_empty": True}}
    return {
        "and": [
            {"property": link_column, "url": {"is_empty": True}},
            {"property": ingredients_column, "rich_text": {"is_empty": True}},
        ],
    }


def ensure_manual_backfill_notion_view_url(db: NotionRecipesDB) -> str:
    """Return a Notion URL for the manual-backfill filtered table view (create or reuse)."""
    client = db._client
    database_id = db._database_id
    data_source_id = db._data_source_id
    filter_obj = manual_backfill_notion_filter(db.schema)

    for item in client.views.list(database_id=database_id).get("results", []):
        view = client.views.retrieve(view_id=item["id"])
        if view.get("name") == _MANUAL_BACKFILL_VIEW_NAME:
            updated = client.views.update(view_id=view["id"], filter=filter_obj)
            return str(updated["url"])

    created = client.views.create(
        database_id=database_id,
        data_source_id=data_source_id,
        name=_MANUAL_BACKFILL_VIEW_NAME,
        type="table",
        filter=filter_obj,
    )
    return str(created["url"])
