"""AppTest smoke tests for NYT sync controls on the Add Recipe tab."""

from __future__ import annotations

from unittest.mock import patch

from ui_source import APP_PATH


def test_nyt_sync_controls_only_on_add_recipe_tab() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "render_nyt_sync_controls" not in app
    add_recipe = (APP_PATH.parent / "sections" / "add_recipe.py").read_text(encoding="utf-8")
    assert "render_nyt_sync_controls()" in add_recipe


def test_nyt_sync_visible_on_add_recipe_when_credentials_missing() -> None:
    from streamlit.testing.v1 import AppTest

    with patch(
        "src.grocery_wizard.ui.nyt_sync.credentials_status",
        return_value={"configured": False, "regi_id": None},
    ):
        at = AppTest.from_file(str(APP_PATH), default_timeout=60)
        at.run()
        tab_picker = at.segmented_control[0]
        tab_picker.set_value("Add Recipe").run()

    assert not at.exception
    markdown_text = " ".join(m.value for m in at.markdown if m.value)
    caption_text = " ".join(c.value for c in at.caption if c.value)
    assert "Sync from NYT Cooking" in markdown_text
    assert "Sync a NYT Cooking recipe-box folder." in caption_text
    assert any("NYT credentials are not set" in w.value for w in at.warning)
    assert not any((expander.label or "") == "Sync from NYT Cooking" for expander in at.expander)


def test_list_recipe_box_folders_omits_all_saved_recipes_option() -> None:
    nyt_sync = (APP_PATH.parent / "nyt_sync.py").read_text(encoding="utf-8")
    nyt_cooking = (APP_PATH.parent.parent / "integrations" / "nyt_cooking.py").read_text(
        encoding="utf-8"
    )
    assert "All saved recipes" not in nyt_sync
    assert '_PREFERRED_NYT_FOLDER_LABELS = ("To make", "Favorites")' in nyt_cooking
    assert 'label="All saved recipes"' not in nyt_cooking


def test_nyt_sync_shows_progress_bar_during_run() -> None:
    nyt_sync = (APP_PATH.parent / "nyt_sync.py").read_text(encoding="utf-8")
    assert 'key="nyt_sync_progress"' in nyt_sync
    assert "st.progress" in nyt_sync
    assert "expected_recipe_count=folder.recipe_count" in nyt_sync
    assert "Sync log" in nyt_sync


def test_nyt_dry_run_defaults_off_and_clarifies_notion_outcome() -> None:
    nyt_sync = (APP_PATH.parent / "nyt_sync.py").read_text(encoding="utf-8")
    assert 'key="nyt_sync_dry_run"' in nyt_sync
    assert "value=False" in nyt_sync
    assert "Dry run finished — Notion was not updated." in nyt_sync
    assert "Notion updated — added" in nyt_sync
    assert "Notion updated — no new recipes were needed" in nyt_sync
