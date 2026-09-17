"""Regression tests for Add Recipe three-way entry layout (issue #198)."""

from __future__ import annotations

from ui_source import UI_ROOT, ui_source

_ADD_RECIPE_SOURCE = (UI_ROOT / "sections" / "add_recipe.py").read_text(encoding="utf-8")


def test_add_recipe_surfaces_three_entry_paths_without_collapsed_expanders() -> None:
    source = ui_source()
    assert "Choose one of three ways to add recipes to Notion." in source
    assert source.count("st.container(border=True)") >= 3
    assert "**Recipe URL**" in source
    assert "**Sync from NYT Cooking**" in source
    assert "Sync all saved recipes from your NYT Cooking recipe-box folder." in source
    assert "**Type it in myself**" in source
    assert 'st.expander("Type it in myself"' not in source


def test_add_recipe_review_expanders_render_inside_entry_sections() -> None:
    source = _ADD_RECIPE_SOURCE
    assert source.count("_render_previews_for_entry(db, schema, previews,") == 3

    url_block = source.split("**Recipe URL**", maxsplit=1)[1].split(
        "**Type it in myself**", maxsplit=1
    )[0]
    manual_block = source.split("**Type it in myself**", maxsplit=1)[1].split(
        "**Sync from NYT Cooking**", maxsplit=1
    )[0]
    nyt_block = source.split("**Sync from NYT Cooking**", maxsplit=1)[1].split(
        "\ndef _preview_dict", maxsplit=1
    )[0]

    assert "_render_previews_for_entry(db, schema, previews, _ENTRY_PATH_URL)" in url_block
    assert "_render_previews_for_entry(db, schema, previews, _ENTRY_PATH_MANUAL)" in manual_block
    assert "_render_previews_for_entry(db, schema, previews, _ENTRY_PATH_NYT)" in nyt_block
    assert (
        "for index, preview in enumerate(previews):"
        not in source.split("def render_add_recipe", maxsplit=1)[1].split(
            "\ndef _preview_dict", maxsplit=1
        )[0]
    )
