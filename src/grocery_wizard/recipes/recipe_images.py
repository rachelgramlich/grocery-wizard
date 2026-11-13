"""Notion Files column helpers for recipe cover images."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import NotionRecipesDB

DEFAULT_RECIPE_IMAGE_FILES_COLUMN = "Image"
_FALLBACK_IMAGE_COLUMN_NAMES = ("Files", "Cover image", "Recipe image", "Photo")


def recipe_image_files_column_name(db: NotionRecipesDB) -> str | None:
    """Return the configured Notion ``files`` column when present in schema."""
    configured = db._config.recipe_image_files_column
    candidates: list[str] = []
    if configured and configured.strip():
        candidates.append(configured.strip())
    if DEFAULT_RECIPE_IMAGE_FILES_COLUMN not in candidates:
        candidates.append(DEFAULT_RECIPE_IMAGE_FILES_COLUMN)
    for name in _FALLBACK_IMAGE_COLUMN_NAMES:
        if name not in candidates:
            candidates.append(name)
    for name in candidates:
        column = db.schema.all_columns.get(name)
        if column is not None and column.type == "files":
            return name
    return None


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
