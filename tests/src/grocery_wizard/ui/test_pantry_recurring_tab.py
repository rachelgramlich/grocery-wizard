"""Tests for pantry page layout and helpers."""

from __future__ import annotations

from ui_source import APP_PATH, pantry_page_source


def test_weekly_page_is_first_and_default() -> None:
    nav = (APP_PATH.parent / "pages" / "__init__.py").read_text(encoding="utf-8")
    assert 'PAGE_LABEL_WEEKLY: Final = "Create weekly plan"' in nav
    assert "PAGE_PICKER_LABELS" in nav
    app = APP_PATH.read_text(encoding="utf-8")
    assert "st.segmented_control(" in app
    assert "_init_page_navigation_state()" in app
    assert "if active_slug == PAGE_SLUG_WEEKLY:" in app
    assert "render_create_weekly_plan()" in app


def test_pantry_and_recurring_share_one_page() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    pantry_fn = pantry_page_source()
    assert "def render_pantry_and_recurring()" in pantry_fn
    assert "elif active_slug == PAGE_SLUG_ADD:" in app
    assert "render_pantry_and_recurring()" in app
    assert "### Pantry" in pantry_fn
    assert "### Recurring weekly items" in pantry_fn
    assert pantry_fn.index("### Recurring weekly items") < pantry_fn.index("### Pantry")
    assert "Save recurring template" not in pantry_fn
    assert "load_store_aisles" in pantry_fn
    assert '"Store aisle"' in pantry_fn
    assert "store_aisles.txt" not in pantry_fn
    assert "Search pantry" in pantry_fn
    assert "st.expander" in pantry_fn
    assert "pantry_tab_remove_pick" not in pantry_fn
    assert "invalidate_notion_cache()" in pantry_fn
    assert "_append_pantry_item_idempotent(name, aisle_label=aisle_name)" in pantry_fn
