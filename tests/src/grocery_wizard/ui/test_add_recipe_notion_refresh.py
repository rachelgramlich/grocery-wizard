"""Regression tests for Add Recipe ingredient lines after Notion cache refresh (#288)."""

from __future__ import annotations

from ui_source import APP_PATH, UI_ROOT


def test_add_recipe_ingredients_text_area_uses_session_state_not_value_kwarg() -> None:
    """Keyed text_area must not pass value= so reruns keep edited lines (e.g. after Refresh)."""
    source = (UI_ROOT / "pages" / "add_recipe.py").read_text(encoding="utf-8")
    ingredients_block = source.split("schema.ingredients_column:", 1)[1].split(
        "schema.instructions_column:", 1
    )[0]
    assert "if widget_key not in st.session_state:" in ingredients_block
    assert "st.session_state[widget_key] = value or" in ingredients_block
    assert "value=value" not in ingredients_block


def test_add_recipe_source_imports_add_recipe_section_from_app() -> None:
    """Sanity: Add Recipe section is wired from app entry (AppTest smoke anchor)."""
    app = APP_PATH.read_text(encoding="utf-8")
    assert "render_add_recipe" in app
