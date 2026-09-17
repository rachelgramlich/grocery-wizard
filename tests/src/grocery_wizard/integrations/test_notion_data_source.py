"""Tests for shared Notion data_source_id resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.integrations.notion_data_source import resolve_notion_data_source_id


def test_resolve_uses_configured_id() -> None:
    databases = MagicMock()
    data_sources = MagicMock()
    assert (
        resolve_notion_data_source_id(
            databases,
            data_sources,
            "db-1",
            configured_id="forced-ds",
        )
        == "forced-ds"
    )
    databases.retrieve.assert_not_called()


def test_resolve_single_source() -> None:
    databases = MagicMock()
    databases.retrieve.return_value = {"data_sources": [{"id": "only-ds"}]}
    data_sources = MagicMock()
    assert resolve_notion_data_source_id(databases, data_sources, "db-1") == "only-ds"


def test_resolve_prefers_link_property() -> None:
    databases = MagicMock()
    databases.retrieve.return_value = {
        "data_sources": [{"id": "ds-a"}, {"id": "ds-b"}],
    }
    data_sources = MagicMock()

    def _retrieve(*, data_source_id: str) -> dict:
        if data_source_id == "ds-a":
            return {"properties": {"Name": {}}}
        return {"properties": {"Link": {}, "Name": {}}}

    data_sources.retrieve.side_effect = _retrieve
    assert (
        resolve_notion_data_source_id(
            databases,
            data_sources,
            "db-1",
            prefer_property="Link",
        )
        == "ds-b"
    )


def test_resolve_raises_when_no_sources() -> None:
    databases = MagicMock()
    databases.retrieve.return_value = {"data_sources": []}
    with pytest.raises(ValueError, match="No data sources"):
        resolve_notion_data_source_id(databases, MagicMock(), "db-1")
