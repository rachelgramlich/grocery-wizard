"""Background ingredient index warm."""

from __future__ import annotations

import time
from unittest.mock import patch

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.ui import ingredient_index_warm as warm_mod


def _recipe(page_id: str, ingredients: str) -> Recipe:
    return Recipe(
        page_id=page_id,
        name="Soup",
        link=None,
        ingredients=ingredients,
        properties={},
    )


def test_schedule_warm_populates_index(monkeypatch) -> None:
    warm_mod.clear_ingredient_index_warm()
    recipes = [_recipe("a", "1 onion")]

    with patch.object(warm_mod, "build_ingredient_index", return_value={"a": {"onion"}}) as build:
        warm_mod.schedule_ingredient_index_warm(recipes)
        deadline = time.monotonic() + 2.0
        key = warm_mod.recipes_ingredient_cache_key(recipes)
        result = None
        while time.monotonic() < deadline:
            result = warm_mod.warmed_ingredient_index_if_ready(key)
            if result is not None:
                break
            time.sleep(0.02)

    assert result == {"a": {"onion"}}
    build.assert_called_once()
