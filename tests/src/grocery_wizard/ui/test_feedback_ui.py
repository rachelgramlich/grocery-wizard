"""AppTest and source checks for the Send feedback control."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from ui_source import (
    app_source,
    apptest_start_app,
    feedback_component_source,
)

if TYPE_CHECKING:
    import pytest


def test_feedback_header_controls_render_in_app() -> None:
    at = apptest_start_app(timeout=60)
    labels = {button.label for button in at.button}
    assert "Refresh from Notion" in labels
    assert "Submit feedback" in labels


def test_submit_feedback_appends_latest_list_debug_log(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_submit(text: str, *, surface: str | None = None) -> str:
        captured["text"] = text
        captured["surface"] = surface or ""
        return "issue #1"

    monkeypatch.setattr("src.grocery_wizard.ui.components.feedback.submit_feedback", fake_submit)

    import streamlit as st

    from src.grocery_wizard.shopping.list_log import ListTrace, build_list_log

    trace = ListTrace()
    debug_log = build_list_log(
        trace,
        meals=["Soup"],
        exclude_pantry=False,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=["flour"],
    )
    st.session_state["grocery_result"] = {
        "debug_log": debug_log,
        "debug_log_notion_url": "https://www.notion.so/testlogpage",
    }
    st.session_state["gw_feedback_note"] = "Milk showed up twice"

    from src.grocery_wizard.ui.components.feedback import _submit_feedback

    _submit_feedback(surface="weekly")
    assert "https://www.notion.so/testlogpage" in captured["text"]
    assert "Milk showed up twice" in captured["text"]
    assert '"final_list"' in captured["text"]


def test_feedback_submit_files_github_issue() -> None:
    from streamlit.testing.v1 import AppTest

    def _app() -> None:
        from src.grocery_wizard.ui.components.feedback import render_feedback_controls

        render_feedback_controls(surface="weekly")

    with patch(
        "src.grocery_wizard.ui.components.feedback.submit_feedback",
        return_value="github #42",
    ):
        at = AppTest.from_function(_app, default_timeout=60)
        at.run(timeout=60)

        at.text_area[0].set_value("Papercut: button hard to see").run(timeout=60)
        submit = [b for b in at.button if b.label == "Submit feedback"]
        assert submit, "Submit feedback button missing"
        submit[0].click().run(timeout=60)

    assert not at.exception
    assert any("Thanks" in s.value and "#42" in s.value for s in at.success)


def test_feedback_control_placed_before_page_picker() -> None:
    app = app_source()
    main_body = app.split("def main() -> None:")[1].split('if __name__ == "__main__"')[0]
    header_idx = main_body.index("_render_global_header_controls")
    picker_idx = main_body.index("_render_page_picker(")
    assert header_idx < picker_idx

    feedback_source = feedback_component_source()
    assert 'st.popover(\n        "Send feedback"' in feedback_source
