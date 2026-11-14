"""Tests for Notion-backed grocery list debug logs."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.grocery_wizard.integrations.notion_list_logs import (
    LIST_LOG_JSON_COLUMN,
    LIST_LOG_NAME_COLUMN,
    LIST_LOG_TYPE_VALUE,
    WEEKLY_LIST_LOG_TITLE_PREFIX,
    NotionListDebugLogsDB,
    list_log_notion_title,
    persist_list_log_to_notion,
)
from src.grocery_wizard.integrations.notion_table import NotionPageRow
from src.grocery_wizard.shopping.list_log import ListTrace, build_list_log


def test_list_log_notion_title_includes_meals() -> None:
    log = {
        "created_at": datetime(2026, 10, 30, 15, 30, tzinfo=UTC).isoformat(),
        "meals": [{"name": "Tacos"}, {"name": "Soup"}],
    }
    title = list_log_notion_title(log)
    assert title.startswith(WEEKLY_LIST_LOG_TITLE_PREFIX)
    assert "Tacos" in title
    assert "2026-10-30" in title


@patch("src.grocery_wizard.integrations.notion.list_logs.NotionDatabase")
def test_save_log_rejects_non_rich_text_json_column(mock_db_cls: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.column_types = {
        LIST_LOG_NAME_COLUMN: "title",
        LIST_LOG_JSON_COLUMN: "url",
    }
    mock_db_cls.return_value = mock_db
    with pytest.raises(ValueError, match="Notion Text"):
        NotionListDebugLogsDB(MagicMock(notion_debug_logs_database_id="logs-db"))


@patch("src.grocery_wizard.integrations.notion.list_logs.NotionDatabase")
def test_save_log_creates_page_with_text_json_column(mock_db_cls: MagicMock) -> None:
    from src.grocery_wizard.integrations.notion_table import write_notion_property

    mock_db = MagicMock()
    mock_db.column_types = {
        LIST_LOG_NAME_COLUMN: "title",
        LIST_LOG_JSON_COLUMN: "text",
        "Type": "select",
    }
    mock_db.property_payload.side_effect = lambda column, value: {
        column: write_notion_property(mock_db.column_types[column], value)
    }
    mock_db.create_page.return_value = NotionPageRow(page_id="page-text", properties={})
    mock_db_cls.return_value = mock_db

    trace = ListTrace()
    log = build_list_log(
        trace,
        meals=["Tacos"],
        exclude_pantry=True,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=["bananas"],
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    db = NotionListDebugLogsDB(MagicMock(notion_debug_logs_database_id="logs-db"))
    assert db.save_log(log) == "page-text"
    props = mock_db.create_page.call_args[0][0]
    assert "text" in props[LIST_LOG_JSON_COLUMN]
    assert props[LIST_LOG_JSON_COLUMN]["text"][0]["text"]["content"].startswith("{")


@patch("src.grocery_wizard.integrations.notion.list_logs.NotionDatabase")
def test_save_log_creates_page(mock_db_cls: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.column_types = {
        LIST_LOG_NAME_COLUMN: "title",
        LIST_LOG_JSON_COLUMN: "rich_text",
        "Type": "select",
    }
    mock_db.property_payload.side_effect = lambda column, value: {column: value}
    mock_db.create_page.return_value = NotionPageRow(page_id="page-1", properties={})
    mock_db_cls.return_value = mock_db

    trace = ListTrace()
    log = build_list_log(
        trace,
        meals=["Tacos"],
        exclude_pantry=True,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=[],
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    db = NotionListDebugLogsDB(MagicMock(notion_debug_logs_database_id="logs-db"))
    page_id = db.save_log(log)
    assert page_id == "page-1"
    mock_db.create_page.assert_called_once()
    create_kwargs = mock_db.create_page.call_args[0][0]
    assert create_kwargs["Type"] == LIST_LOG_TYPE_VALUE


@patch("src.grocery_wizard.integrations.notion.list_logs.NotionListDebugLogsDB")
def test_persist_list_log_swallows_errors(mock_db_cls: MagicMock) -> None:
    mock_db_cls.side_effect = RuntimeError("network")
    page_id, url = persist_list_log_to_notion({"created_at": "2026-10-30T12:00:00+00:00"})
    assert page_id is None
    assert url is None


def test_persist_list_log_update_path() -> None:
    with patch(
        "src.grocery_wizard.integrations.notion.list_logs.NotionListDebugLogsDB"
    ) as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        page_id, url = persist_list_log_to_notion(
            {"created_at": "2026-10-30T12:00:00+00:00"},
            page_id="abc-def",
        )
    mock_db.update_log.assert_called_once_with(
        "abc-def", {"created_at": "2026-10-30T12:00:00+00:00"}
    )
    assert page_id == "abc-def"
    assert url == "https://www.notion.so/abcdef"
