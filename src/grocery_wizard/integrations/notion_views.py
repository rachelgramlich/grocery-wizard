"""Notion database views used by the Streamlit UI."""

from __future__ import annotations

__all__ = [
    "clear_notion_view_url_cache",
    "ensure_manual_ingredients_notion_view_url",
    "ensure_notion_filtered_view_url",
    "ensure_possibly_missing_checkboxes_notion_view_url",
    "manual_ingredients_notion_filter",
    "possibly_missing_checkboxes_notion_filter",
]

import json
from typing import Any

from src.grocery_wizard.integrations.notion import DatabaseSchema, NotionRecipesDB

_MANUAL_INGREDIENTS_VIEW_NAME = "Grocery Wizard — manual ingredients"
_POSSIBLY_MISSING_CHECKBOXES_VIEW_NAME = "Grocery Wizard — possibly missing checkboxes"


# Views rarely change, but ensuring one costs a list + retrieve per existing view (~20 requests).
# Cache per process so opening the maintenance page does not hit Notion on every render.
_VIEW_URL_CACHE: dict[tuple[str, str, str], str] = {}
_VIEW_IDS_BY_DATABASE: dict[str, dict[str, str]] = {}


def clear_notion_view_url_cache() -> None:
    """Forget remembered view URLs (use after a manual refresh from Notion)."""
    _VIEW_URL_CACHE.clear()
    _VIEW_IDS_BY_DATABASE.clear()


def _view_ids_by_name(client: Any, database_id: str) -> dict[str, str]:
    if database_id not in _VIEW_IDS_BY_DATABASE:
        ids: dict[str, str] = {}
        for item in client.views.list(database_id=database_id).get("results", []):
            view = client.views.retrieve(view_id=item["id"])
            ids.setdefault(str(view.get("name")), str(view["id"]))
        _VIEW_IDS_BY_DATABASE[database_id] = ids
    return _VIEW_IDS_BY_DATABASE[database_id]


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
    cache_key = (database_id, view_name, json.dumps(filter_obj, sort_keys=True))
    cached_url = _VIEW_URL_CACHE.get(cache_key)
    if cached_url is not None:
        return cached_url

    view_ids = _view_ids_by_name(client, database_id)
    existing_id = view_ids.get(view_name)
    if existing_id is not None:
        url = str(client.views.update(view_id=existing_id, filter=filter_obj)["url"])
    else:
        created = client.views.create(
            database_id=database_id,
            data_source_id=db._data_source_id,
            name=view_name,
            type="table",
            filter=filter_obj,
        )
        view_ids[view_name] = str(created["id"])
        url = str(created["url"])
    _VIEW_URL_CACHE[cache_key] = url
    return url


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
