"""Regression tests for grocery list display in the Streamlit UI."""

from __future__ import annotations

from pathlib import Path

from ui_source import ui_source

from src.grocery_wizard.integrations.notion import Recipe, notion_page_url, recipe_export_link
from src.grocery_wizard.shopping.grocery_list import (
    format_grocery_items_copy_text,
    format_meals_and_grocery_list,
    format_meals_copy_text,
)
from src.grocery_wizard.ui.grocery_helpers import compute_grocery_drafts, meal_entries_with_links


def test_grocery_final_list_syncs_session_state_before_keyed_text_area() -> None:
    """Keyed text_area ignores value= on reruns; app must push fresh list_text into session state."""
    source = ui_source()
    assert 'st.session_state["grocery_final_list"] = grocery_copy_text' in source
    assert 'key="grocery_final_list"' in source
    assert "value=list_text" not in source


def test_keyed_text_area_with_session_state_sync_updates_on_rerun(tmp_path: Path) -> None:
    """Session-state sync before keyed text_area refreshes display on reruns."""
    from streamlit.testing.v1 import AppTest

    test_app = """
import streamlit as st

if "counter" not in st.session_state:
    st.session_state.counter = 0

if st.button("increment"):
    st.session_state.counter += 1

computed = f"Value: {st.session_state.counter}"
st.session_state["display_key"] = computed
st.text_area("display", key="display_key")
"""
    app_file = tmp_path / "streamlit_sync_widget_fixture.py"
    app_file.write_text(test_app, encoding="utf-8")

    at = AppTest.from_file(str(app_file), default_timeout=30)
    at.run()
    at.button[0].click().run()

    assert at.text_area[0].value == "Value: 1"


def test_recipe_export_link_prefers_external_url() -> None:
    recipe = Recipe(
        page_id="abc123de-f456-7890-abcd-ef1234567890",
        name="Soup",
        link="https://example.com/soup",
        ingredients=None,
        properties={},
    )
    assert recipe_export_link(recipe) == "https://example.com/soup"


def test_recipe_export_link_falls_back_to_notion_page() -> None:
    page_id = "abc123de-f456-7890-abcd-ef1234567890"
    recipe = Recipe(
        page_id=page_id,
        name="Manual Recipe",
        link=None,
        ingredients="salt",
        properties={},
    )
    assert recipe_export_link(recipe) == notion_page_url(page_id)
    assert recipe_export_link(recipe) == "https://www.notion.so/abc123def4567890abcdef1234567890"


def test_meal_entries_with_links_uses_notion_when_link_blank() -> None:
    page_id = "11111111-2222-3333-4444-555555555555"
    recipes = [
        Recipe(
            page_id=page_id,
            name="No Link Recipe",
            link="",
            ingredients=None,
            properties={},
        ),
    ]
    meals = meal_entries_with_links(["No Link Recipe"], recipes)
    assert format_meals_copy_text(meals) == (f"- No Link Recipe ({notion_page_url(page_id)})")


def test_copy_text_excludes_section_header_lines() -> None:
    meals = [("Soup", "https://example.com/soup")]
    grocery_items = ["onions", "milk"]

    meals_copy = format_meals_copy_text(meals)
    grocery_copy = format_grocery_items_copy_text(grocery_items)

    assert meals_copy == "- Soup (https://example.com/soup)"
    assert "Meals" not in meals_copy.splitlines()
    assert grocery_copy == "- onions\n- milk"
    assert "Grocery List" not in grocery_copy.splitlines()
    assert "grocery list" not in grocery_copy.lower().splitlines()


def test_format_meals_and_grocery_list_keeps_aisle_sort_without_headers() -> None:
    """Copy output is flat but still ordered by store walk (sort_grocery_items)."""
    meals: list[tuple[str, str | None]] = []
    grocery_items = ["onions", "Bananas", "Flowers"]

    text = format_meals_and_grocery_list(meals, grocery_items)

    assert "Vegetables" not in text
    assert "Fruit" not in text
    flowers_pos = text.lower().index("flowers")
    bananas_pos = text.lower().index("bananas")
    onions_pos = text.lower().index("onions")
    assert flowers_pos < bananas_pos < onions_pos


def test_compute_grocery_drafts_merges_recurring_items_into_final_list() -> None:
    """Recurring template lines must appear on the export list, not only in the summary."""
    base_items = ["bananas", "berries", "1 lb chicken"]
    recurring = ["milk", "fruit"]
    _, final_items = compute_grocery_drafts(
        base_items,
        [],
        "",
        recurring_items=recurring,
    )
    assert "milk" in final_items
    assert "fruit" in final_items


def test_user_flow_checklist_extras_strip_sort_dedupe() -> None:
    """Simulate pasting Notion checklist extras through the UI display pipeline."""
    extra_items_text = "- [ ] Bananas\n- [ ] Flowers\n- [ ] Bananas"
    base_items = ["onions"]

    _, final_items = compute_grocery_drafts(base_items, [], extra_items_text)
    list_text = format_meals_and_grocery_list([], final_items)

    assert "[ ]" not in list_text
    assert "[x]" not in list_text.lower()
    assert list_text.lower().count("bananas") == 1
    assert "flowers" in list_text.lower()
    assert "onions" in list_text.lower()
    assert "Vegetables" not in list_text
    assert "Fruit" not in list_text
    # Store walk order without aisle headers
    flowers_pos = list_text.lower().index("flowers")
    bananas_pos = list_text.lower().index("bananas")
    onions_pos = list_text.lower().index("onions")
    assert flowers_pos < bananas_pos < onions_pos
