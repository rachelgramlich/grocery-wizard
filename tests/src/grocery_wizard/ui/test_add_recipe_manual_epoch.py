"""Manual add-recipe widget keys rotate so a new blank recipe does not reuse stale fields."""

from __future__ import annotations

from ui_source import add_recipe_page_source


def test_manual_recipe_start_bumps_epoch_for_widget_keys() -> None:
    add_recipe = add_recipe_page_source()
    assert "add_recipe_manual_epoch" in add_recipe
    assert "_MANUAL_RECIPE_EPOCH_KEY" in add_recipe
    assert "_recipe_editor_key_prefix" in add_recipe
    assert 'return f"recipe_manual_{epoch}_{index}"' in add_recipe
