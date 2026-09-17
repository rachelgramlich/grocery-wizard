"""Regression tests for Add Recipe tab UX (issue #206)."""

from __future__ import annotations

from ui_source import ui_source


def test_add_recipe_tab_avoids_duplicate_add_recipe_heading() -> None:
    source = ui_source()
    assert 'st.subheader("Add Recipe")' not in source


def test_add_recipe_entry_sections_ordered_url_manual_nyt() -> None:
    source = ui_source()
    url_pos = source.index("**Recipe URL**")
    manual_pos = source.index("**Type it in myself**")
    nyt_pos = source.index("**Sync from NYT Cooking**")
    assert url_pos < manual_pos < nyt_pos


def test_manual_blank_recipe_uses_primary_button() -> None:
    source = ui_source()
    manual_block = source.split("**Type it in myself**", maxsplit=1)[1].split(
        "**Sync from NYT Cooking**", maxsplit=1
    )[0]
    assert '"Start blank recipe"' in manual_block
    assert 'type="primary"' in manual_block
