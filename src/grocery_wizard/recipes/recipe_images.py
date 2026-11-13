"""Notion Files column helpers for recipe cover images."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import DatabaseSchema, Recipe


def _files_entries(prop: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not prop or prop.get("type") != "files":
        return []
    items = prop.get("files")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def files_property_has_attachment(prop: dict[str, Any] | None) -> bool:
    """True when the raw Notion files property has at least one attachment."""
    return bool(_files_entries(prop))


def read_files_property_names(prop: dict[str, Any] | None) -> list[str] | None:
    """Human-facing file labels for ``Recipe.properties`` (maintenance / backfill)."""
    names: list[str] = []
    for item in _files_entries(prop):
        name = str(item.get("name") or "").strip()
        if name:
            names.append(name)
            continue
        if item.get("type") == "file":
            file_meta = item.get("file") or {}
            if isinstance(file_meta, dict) and file_meta.get("url"):
                names.append("file")
        if item.get("type") == "file_upload":
            names.append(name or "file")
    return names or None


def read_files_property_url(prop: dict[str, Any] | None) -> str | None:
    """First HTTP(S) URL from a Notion files property when the API exposes one."""
    for entry in _files_entries(prop):
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
        elif entry_type == "file_upload":
            upload_meta = entry.get("file_upload")
            if isinstance(upload_meta, dict):
                url = upload_meta.get("url")
                if isinstance(url, str) and url.strip():
                    return url.strip()
    return None


def recipe_has_cover_image(recipe: Recipe, schema: DatabaseSchema) -> bool:
    """True when the recipe's configured Files column has an attachment (with or without URL)."""
    column = schema.image_column
    if not column:
        return False
    if recipe.image_file_url:
        return True
    value = recipe.properties.get(column)
    return isinstance(value, list) and bool(value)
