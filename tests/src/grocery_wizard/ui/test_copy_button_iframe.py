"""Regression: copy buttons use st.iframe, not deprecated components.v1.html."""

from __future__ import annotations

from ui_source import grocery_helpers_source


def test_render_copy_button_uses_st_iframe() -> None:
    source = grocery_helpers_source()
    fn = source.split("def render_copy_button", 1)[1].split("\ndef ", 1)[0]
    assert "st.iframe(" in fn
    assert "components.v1" not in source
    assert "components.html" not in source
