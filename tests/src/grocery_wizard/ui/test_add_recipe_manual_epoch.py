"""Manual add-recipe widget keys rotate so a new blank recipe does not reuse stale fields."""

from __future__ import annotations

from ui_source import UI_ROOT

_ADD_RECIPE_SOURCE = (UI_ROOT / "sections" / "add_recipe.py").read_text(encoding="utf-8")


def test_manual_recipe_start_bumps_epoch_for_widget_keys() -> None:
    assert "add_recipe_manual_epoch" in _ADD_RECIPE_SOURCE
    assert "_MANUAL_RECIPE_EPOCH_KEY" in _ADD_RECIPE_SOURCE
    assert "_recipe_editor_key_prefix" in _ADD_RECIPE_SOURCE
    assert 'return f"recipe_manual_{epoch}_{index}"' in _ADD_RECIPE_SOURCE
