"""AppTest smoke tests for NYT sync controls on the Add Recipe tab."""

from __future__ import annotations

from unittest.mock import patch

from ui_source import APP_PATH


def test_nyt_sync_controls_only_on_add_recipe_tab() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "render_nyt_sync_controls" not in app
    add_recipe = (APP_PATH.parent / "sections" / "add_recipe.py").read_text(encoding="utf-8")
    assert "render_nyt_sync_controls()" in add_recipe


def test_nyt_sync_expander_renders_when_credentials_missing() -> None:
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
    assert any("Sync from NYT Cooking" in (expander.label or "") for expander in at.expander)
    assert any("NYT credentials are not set" in w.value for w in at.warning)
