"""Notion database views used by the Streamlit UI."""

from __future__ import annotations

from typing import Any

from src.grocery_wizard.integrations.notion import DatabaseSchema, NotionRecipesDB

_MANUAL_INGREDIENTS_VIEW_NAME = "Grocery Wizard — manual ingredients"
_POSSIBLY_MISSING_CHECKBOXES_VIEW_NAME = "Grocery Wizard — possibly missing checkboxes"


def manual_ingredients_notion_filter(schema: DatabaseSchema) -> dict[str, Any]:
    """Filter: Link empty and Ingredients empty (cannot auto-scrape; edit in Notion)."""
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


def possibly_missing_checkboxes_notion_filter(schema: DatabaseSchema) -> dict[str, Any]:
    """Filter: every review checkbox is unchecked (possibly unset — not definitely wrong)."""
    checkbox_columns = schema.checkbox_columns
    if not checkbox_columns:
        return {"property": schema.link_column, "url": {"is_not_empty": True}}
    clauses = [{"property": col.name, "checkbox": {"equals": False}} for col in checkbox_columns]
    if len(clauses) == 1:
        return clauses[0]
    return {"and": clauses}


def ensure_notion_filtered_view_url(
    db: NotionRecipesDB,
    *,
    view_name: str,
    filter_obj: dict[str, Any],
) -> str:
    """Return a Notion URL for a named filtered table view (create or reuse)."""
    client = db._client
    database_id = db._database_id
    data_source_id = db._data_source_id

    for item in client.views.list(database_id=database_id).get("results", []):
        view = client.views.retrieve(view_id=item["id"])
        if view.get("name") == view_name:
            updated = client.views.update(view_id=view["id"], filter=filter_obj)
            return str(updated["url"])

    created = client.views.create(
        database_id=database_id,
        data_source_id=data_source_id,
        name=view_name,
        type="table",
        filter=filter_obj,
    )
    return str(created["url"])


def ensure_manual_ingredients_notion_view_url(db: NotionRecipesDB) -> str:
    return ensure_notion_filtered_view_url(
        db,
        view_name=_MANUAL_INGREDIENTS_VIEW_NAME,
        filter_obj=manual_ingredients_notion_filter(db.schema),
    )


def ensure_possibly_missing_checkboxes_notion_view_url(db: NotionRecipesDB) -> str:
    return ensure_notion_filtered_view_url(
        db,
        view_name=_POSSIBLY_MISSING_CHECKBOXES_VIEW_NAME,
        filter_obj=possibly_missing_checkboxes_notion_filter(db.schema),
    )
