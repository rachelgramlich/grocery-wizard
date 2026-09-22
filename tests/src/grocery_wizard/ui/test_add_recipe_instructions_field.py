"""Add Recipe UI exposes Instructions as a text area in the review form."""

from __future__ import annotations

from ui_source import UI_ROOT

_ADD_RECIPE_SOURCE = (UI_ROOT / "sections" / "add_recipe.py").read_text(encoding="utf-8")


def test_add_recipe_review_form_includes_instructions_text_area() -> None:
    assert "schema.instructions_column" in _ADD_RECIPE_SOURCE
    block = _ADD_RECIPE_SOURCE.split("def _render_recipe_field_editors", maxsplit=1)[1]
    assert "elif field_name == schema.instructions_column:" in block
    assert "st.text_area(" in block.split("schema.instructions_column", maxsplit=1)[1]
