"""Regression tests for Notion cache invalidation (issue #320)."""

from __future__ import annotations

from ui_source import UI_ROOT

_NOTION_CACHE_PATH = UI_ROOT / "notion_cache.py"


def test_invalidate_notion_cache_clears_cached_db_resource() -> None:
    source = _NOTION_CACHE_PATH.read_text(encoding="utf-8")
    invalidate_block = source.split("def invalidate_notion_cache()", 1)[1].split("\n\n", 1)[0]
    assert "get_db.clear()" in invalidate_block
