"""Resolve Notion database data_source_id (API 2025+ multi-source databases)."""

from __future__ import annotations

from typing import Any, Protocol


class NotionDataSourcesClient(Protocol):
    def retrieve(self, *, data_source_id: str) -> dict[str, Any]: ...


class NotionDatabasesClient(Protocol):
    def retrieve(self, *, database_id: str) -> dict[str, Any]: ...


def resolve_notion_data_source_id(
    databases: NotionDatabasesClient,
    data_sources: NotionDataSourcesClient,
    database_id: str,
    *,
    configured_id: str | None = None,
    prefer_property: str | None = None,
) -> str:
    """Pick the data source that holds row schema and queries for ``database_id``.

    When ``configured_id`` is set (``NOTION_DATA_SOURCE_ID``), it wins.
    With a single data source, that id is used. With multiple sources,
    ``prefer_property`` selects the source whose schema includes that column
    (Recipes DB uses ``Link``); otherwise the first source is used.
    """
    if configured_id:
        return configured_id

    db = databases.retrieve(database_id=database_id)
    sources = db.get("data_sources", [])
    if not sources:
        raise ValueError(f"No data sources found for Notion database {database_id}")
    if len(sources) == 1:
        return sources[0]["id"]

    if prefer_property:
        for entry in sources:
            detail = data_sources.retrieve(data_source_id=entry["id"])
            if prefer_property in detail.get("properties", {}):
                return entry["id"]

    return sources[0]["id"]
