"""Notion database for weekly grocery list build debug logs (one row per build).

Only the weekly grocery list flow writes here today; other app surfaces do not log yet.
"""

from __future__ import annotations

__all__ = [
    "LIST_LOG_BUILT_AT_COLUMN",
    "LIST_LOG_JSON_COLUMN",
    "LIST_LOG_MEALS_COLUMN",
    "LIST_LOG_NAME_COLUMN",
    "LIST_LOG_TYPE_VALUE",
    "WEEKLY_LIST_LOG_TITLE_PREFIX",
    "NotionListDebugLogsDB",
    "list_log_notion_title",
    "persist_list_log_to_notion",
]

import logging
from datetime import UTC, datetime
from typing import Any

from src.grocery_wizard.config import Config, load_config
from src.grocery_wizard.integrations.notion import notion_page_url
from src.grocery_wizard.integrations.notion_table import NotionDatabase
from src.grocery_wizard.shopping.list_log import dump_list_log

LIST_LOG_NAME_COLUMN = "Name"
LIST_LOG_BUILT_AT_COLUMN = "Built at"
LIST_LOG_MEALS_COLUMN = "Meals"
LIST_LOG_JSON_COLUMN = "Log JSON"
LIST_LOG_TYPE_COLUMNS = ("Type", "Surface")
LIST_LOG_TYPE_VALUE = "weekly grocery list"
WEEKLY_LIST_LOG_TITLE_PREFIX = "[weekly list]"

_LOG = logging.getLogger(__name__)


def list_log_notion_title(log: dict[str, Any]) -> str:
    """Short title for the Notion row (timestamp + meal names)."""
    meals = [str(entry.get("name") or "").strip() for entry in log.get("meals", [])]
    meals = [name for name in meals if name]
    created = str(log.get("created_at") or "")
    try:
        dt = datetime.fromisoformat(created)
        stamp = dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        stamp = created[:19] if created else "Grocery list build"
    if not meals:
        body = stamp
    else:
        preview = ", ".join(meals[:3])
        if len(meals) > 3:
            preview = f"{preview} (+{len(meals) - 3} more)"
        body = f"{stamp} · {preview}"
    title = f"{WEEKLY_LIST_LOG_TITLE_PREFIX} {body}"
    return title[:2000]


class NotionListDebugLogsDB:
    """Append/update rows in the household list-debug-log database."""

    def __init__(self, config: Config | None = None) -> None:
        cfg = config or load_config()
        db_id = cfg.notion_debug_logs_database_id
        if not db_id:
            raise ValueError("NOTION_DEBUG_LOGS_DATABASE_ID is required")
        self._db = NotionDatabase(cfg, db_id)
        for column in (LIST_LOG_NAME_COLUMN, LIST_LOG_JSON_COLUMN):
            if column not in self._db.column_types:
                raise ValueError(
                    f"List debug log database needs a {column!r} column "
                    f"(found: {sorted(self._db.column_types)})"
                )

    def save_log(self, log: dict[str, Any]) -> str:
        row = self._db.create_page(self._properties_for_log(log))
        return row.page_id

    def update_log(self, page_id: str, log: dict[str, Any]) -> None:
        props: dict[str, Any] = {}
        props.update(self._db.property_payload(LIST_LOG_JSON_COLUMN, dump_list_log(log)))
        if LIST_LOG_MEALS_COLUMN in self._db.column_types:
            props.update(self._db.property_payload(LIST_LOG_MEALS_COLUMN, _meals_summary(log)))
        self._db.update_page(page_id, props)

    def _properties_for_log(self, log: dict[str, Any]) -> dict[str, Any]:
        props: dict[str, Any] = {}
        props.update(self._db.property_payload(LIST_LOG_NAME_COLUMN, list_log_notion_title(log)))
        props.update(self._db.property_payload(LIST_LOG_JSON_COLUMN, dump_list_log(log)))
        if LIST_LOG_BUILT_AT_COLUMN in self._db.column_types:
            props.update(
                self._db.property_payload(
                    LIST_LOG_BUILT_AT_COLUMN,
                    _built_at_date(log.get("created_at")),
                )
            )
        if LIST_LOG_MEALS_COLUMN in self._db.column_types:
            props.update(self._db.property_payload(LIST_LOG_MEALS_COLUMN, _meals_summary(log)))
        props.update(_optional_type_property(self._db))
        return props


def _optional_type_property(db: NotionDatabase) -> dict[str, Any]:
    for column in LIST_LOG_TYPE_COLUMNS:
        if column in db.column_types:
            return db.property_payload(column, LIST_LOG_TYPE_VALUE)
    return {}


def _meals_summary(log: dict[str, Any]) -> str:
    names = [str(entry.get("name") or "").strip() for entry in log.get("meals", [])]
    names = [name for name in names if name]
    return ", ".join(names)


def _built_at_date(created_at: object) -> str | None:
    if not created_at:
        return None
    try:
        dt = datetime.fromisoformat(str(created_at))
        return dt.astimezone(UTC).date().isoformat()
    except ValueError:
        return None


def persist_list_log_to_notion(
    log: dict[str, Any],
    *,
    config: Config | None = None,
    page_id: str | None = None,
) -> tuple[str | None, str | None]:
    """Write or refresh the log in Notion. Returns ``(page_id, url)``; never raises."""
    try:
        db = NotionListDebugLogsDB(config)
        if page_id:
            db.update_log(page_id, log)
            return page_id, notion_page_url(page_id)
        new_id = db.save_log(log)
        return new_id, notion_page_url(new_id)
    except Exception:
        _LOG.warning("Could not persist grocery list debug log to Notion", exc_info=True)
        return None, None
