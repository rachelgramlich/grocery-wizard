"""Regression tests for issue #205: Refresh from Notion vs active section."""

from __future__ import annotations

from ui_source import APP_PATH


def test_notion_refresh_uses_on_click_not_inline_rerun() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "def _refresh_notion_cache_from_ui()" in app
    assert "on_click=_refresh_notion_cache_from_ui" in app
    refresh_block = app.split("def _render_notion_cache_controls()")[1].split("def main")[0]
    assert "st.rerun()" not in refresh_block


def test_notion_refresh_controls_render_above_section_picker() -> None:
    """Match established layout: refresh row under title, section tabs below it."""
    app = APP_PATH.read_text(encoding="utf-8")
    main_body = app.split("def main() -> None:")[1].split('if __name__ == "__main__"')[0]
    picker_idx = main_body.index('key="gw_active_tab"')
    refresh_idx = main_body.index("_render_notion_cache_controls()")
    assert refresh_idx < picker_idx


def test_active_section_render_is_keyed_container() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "_GW_RENDER_SECTION" in app
    assert 'st.container(key=f"gw_section_{section_key}")' in app
    assert "persist_state=\"session\"" in app


def test_section_body_branches_on_render_section_not_picker_return() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    assert "active_tab = st.session_state[_GW_RENDER_SECTION]" in app
    assert "_sync_render_section_from_picker()" in app
    assert "_SKIP_PICKER_RENDER_SYNC" in app


def test_picker_sync_updates_render_section_without_on_change() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)
    at.segmented_control[0].set_value("Pantry & recurring").run(timeout=60)
    at.session_state["gw_render_section"] = "Weekly recipe generation"
    at.run(timeout=60)
    assert at.session_state["gw_render_section"] == "Pantry & recurring"
    assert not any(s.value == "Create weekly plan" for s in at.subheader)


def test_refresh_keeps_pantry_body_when_picker_state_desyncs() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)
    at.segmented_control[0].set_value("Pantry & recurring").run(timeout=60)
    at.session_state["gw_active_tab"] = "Weekly recipe generation"
    refresh = [b for b in at.button if b.label == "Refresh from Notion"]
    refresh[0].click().run(timeout=60)
    assert not at.exception
    assert at.session_state["gw_render_section"] == "Pantry & recurring"
    assert at.session_state["gw_active_tab"] == "Pantry & recurring"
    assert not any(s.value == "Create weekly plan" for s in at.subheader)


def test_pantry_tab_after_notion_refresh_does_not_show_weekly_plan() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)

    at.segmented_control[0].set_value("Pantry & recurring").run(timeout=60)
    assert not at.exception

    refresh = [b for b in at.button if b.label == "Refresh from Notion"]
    assert refresh, "Refresh from Notion button missing"
    refresh[0].click().run(timeout=60)
    assert not at.exception

    markdown_blob = " ".join(m.value or "" for m in at.markdown)
    assert "Create weekly plan" not in markdown_blob
    assert "### Pantry" in markdown_blob or "### Recurring weekly items" in markdown_blob
