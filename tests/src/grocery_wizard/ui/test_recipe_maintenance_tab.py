"""UI registration for the Recipe maintenance page."""

from __future__ import annotations

from ui_source import APP_PATH, ui_source


def test_recipe_maintenance_page_registered() -> None:
    nav = (APP_PATH.parent / "pages" / "__init__.py").read_text(encoding="utf-8")
    assert 'PAGE_LABEL_MAINTENANCE: Final = "Recipe maintenance"' in nav
    assert "PAGE_PICKER_LABELS" in nav
    source = ui_source()
    assert "def render_recipe_maintenance()" in source
    assert "Start ingredients backfill" in source
    assert "### Automatic backfill" in source
    assert "### Manual backfill in Notion" in source
    assert "Write ingredients in Notion" in source
    assert "Review checkbox columns in Notion" in source
    assert "will appear in Notion with this filter" in source
    assert "st.link_button(" in source
    assert 'type="primary"' in source
    assert "Open in Notion" in source
    assert "Open Notion with this filter" not in source
    assert "Start metadata backfill" in source
    assert "### Meal plan status" in source
    assert "_render_meal_plan_status_section" in source
    assert "Apply meal plan status" in source
    assert source.index("### Meal plan status") < source.index("### Automatic backfill")

    app = APP_PATH.read_text(encoding="utf-8")
    assert "elif active_slug == PAGE_SLUG_MAINTENANCE:" in app
    assert "render_recipe_maintenance()" in app
