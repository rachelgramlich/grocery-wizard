"""AppTest smoke tests for NYT sync controls in app.py."""

from __future__ import annotations

from unittest.mock import patch

from ui_source import APP_PATH


def test_nyt_sync_expander_renders_when_credentials_missing() -> None:
    from streamlit.testing.v1 import AppTest

    with patch(
        "src.grocery_wizard.ui.nyt_sync.credentials_status",
        return_value={"configured": False, "regi_id": None},
    ):
        at = AppTest.from_file(str(APP_PATH), default_timeout=60)
        at.run()

    assert not at.exception
    assert any("Sync from NYT Cooking" in (expander.label or "") for expander in at.expander)
    assert any("NYT credentials are not set" in w.value for w in at.warning)
