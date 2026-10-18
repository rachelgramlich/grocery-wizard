"""Deploy-race fallback when list_saved_plans lacks recipe_names_by_page_id (#417)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.ui import notion_cache


def test_load_saved_plans_cached_falls_back_without_recipe_names_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def _list_saved_plans(*, recipes_db=None, recipe_names_by_page_id=None) -> list:
        calls.append(
            {
                "recipes_db": recipes_db,
                "recipe_names_by_page_id": recipe_names_by_page_id,
            }
        )
        if recipe_names_by_page_id is not None:
            raise TypeError("unexpected keyword argument 'recipe_names_by_page_id'")
        return []

    monkeypatch.setattr(notion_cache, "list_saved_plans", _list_saved_plans)
    monkeypatch.setattr(
        notion_cache,
        "_recipes_from_store",
        lambda _db: [],
    )

    db = MagicMock()
    result = notion_cache._list_saved_plans_for_ui(db, {})

    assert result == []
    assert len(calls) == 2
    assert calls[0]["recipe_names_by_page_id"] == {}
    assert calls[1]["recipe_names_by_page_id"] is None
