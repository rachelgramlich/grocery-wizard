"""Notion Files column helpers for recipe cover images."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import NotionRecipesDB


def recipe_image_files_column_name(db: NotionRecipesDB) -> str | None:
    """Return the recipe Files column from schema (shared with #490 backfill)."""
    return db.schema.image_column


def read_files_property_url(prop: dict[str, object] | None) -> str | None:
    """First HTTP(S) URL from a Notion files property (hosted file or external)."""
    if not prop or prop.get("type") != "files":
        return None
    files = prop.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        if not isinstance(entry, dict):
            continue
        entry_type = entry.get("type")
        if entry_type == "file":
            file_meta = entry.get("file")
            if isinstance(file_meta, dict):
                url = file_meta.get("url")
                if isinstance(url, str) and url.strip():
                    return url.strip()
        elif entry_type == "external":
            external = entry.get("external")
            if isinstance(external, dict):
                url = external.get("url")
                if isinstance(url, str) and url.strip():
                    return url.strip()
    return None
