"""AppTest and source checks for the Send feedback control."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ui_source import APP_PATH

from src.grocery_wizard.lib.feedback_backlog import append_feedback, read_feedback_backlog


def test_feedback_expander_renders_in_app() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)

    assert not at.exception
    assert any("Send feedback" in (expander.label or "") for expander in at.expander)


def test_feedback_submit_appends_to_backlog(tmp_path: Path) -> None:
    from streamlit.testing.v1 import AppTest

    backlog = tmp_path / "feedback_backlog.jsonl"

    def _app() -> None:
        from src.grocery_wizard.ui.feedback import render_feedback_controls

        render_feedback_controls(surface="Weekly recipe generation")

    with patch(
        "src.grocery_wizard.ui.feedback.append_feedback",
        side_effect=lambda text, surface=None: append_feedback(text, path=backlog, surface=surface),
    ):
        at = AppTest.from_function(_app, default_timeout=60)
        at.run(timeout=60)

        at.text_area[0].set_value("Papercut: button hard to see").run(timeout=60)
        submit = [b for b in at.button if b.label == "Submit feedback"]
        assert submit, "Submit feedback button missing"
        submit[0].click().run(timeout=60)

    assert not at.exception
    entries = read_feedback_backlog(backlog)
    assert len(entries) == 1
    assert entries[0]["text"] == "Papercut: button hard to see"
    assert entries[0]["surface"] == "Weekly recipe generation"
    assert any("Thanks" in s.value for s in at.success)


def test_feedback_control_placed_before_section_picker() -> None:
    app = APP_PATH.read_text(encoding="utf-8")
    main_body = app.split("def main() -> None:")[1].split('if __name__ == "__main__"')[0]
    feedback_idx = main_body.index("render_feedback_controls")
    picker_idx = main_body.index('key="gw_active_tab"')
    assert feedback_idx < picker_idx
