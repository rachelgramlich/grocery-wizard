"""UI registration for the Recipe maintenance tab."""

from __future__ import annotations

from ui_source import APP_PATH, ui_source


def test_recipe_maintenance_tab_registered() -> None:
    source = ui_source()
    assert '_TAB_MAINTENANCE = "Recipe maintenance"' in source
    assert "_UI_TABS = (_TAB_WEEKLY, _TAB_ADD, _TAB_PANTRY, _TAB_MAINTENANCE)" in source
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

    app = APP_PATH.read_text(encoding="utf-8")
    assert "elif active_tab == _TAB_MAINTENANCE:" in app
    assert "render_recipe_maintenance()" in app
