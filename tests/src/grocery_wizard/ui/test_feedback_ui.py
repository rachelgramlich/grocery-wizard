"""AppTest and source checks for the Send feedback control."""

from __future__ import annotations

from unittest.mock import patch

from ui_source import APP_PATH


def test_feedback_expander_renders_in_app() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)

    assert not at.exception
    assert any("Send feedback" in (expander.label or "") for expander in at.expander)


def test_feedback_submit_files_github_issue() -> None:
    from streamlit.testing.v1 import AppTest

    def _app() -> None:
        from src.grocery_wizard.ui.feedback import render_feedback_controls

        render_feedback_controls(surface="weekly")

    with patch(
        "src.grocery_wizard.ui.feedback.submit_feedback",
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
    app = APP_PATH.read_text(encoding="utf-8")
    main_body = app.split("def main() -> None:")[1].split('if __name__ == "__main__"')[0]
    feedback_idx = main_body.index("render_feedback_controls")
    picker_idx = main_body.index("st.segmented_control(")
    assert feedback_idx < picker_idx
