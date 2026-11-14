"""Add Recipe UI exposes Instructions as a text area in the review form."""

from __future__ import annotations

from ui_source import add_recipe_page_source


def test_add_recipe_review_form_includes_instructions_text_area() -> None:
    add_recipe = add_recipe_page_source()
    assert "schema.instructions_column" in add_recipe
    block = add_recipe.split("def _render_recipe_field_editors", maxsplit=1)[1]
    assert "elif field_name == schema.instructions_column:" in block
    assert "st.text_area(" in block.split("schema.instructions_column", maxsplit=1)[1]
