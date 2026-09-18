"""Regression: copy buttons use st.iframe, not deprecated components.v1.html."""

from __future__ import annotations

from ui_source import UI_ROOT


def test_render_copy_button_uses_st_iframe() -> None:
    source = (UI_ROOT / "grocery_helpers.py").read_text(encoding="utf-8")
    fn = source.split("def render_copy_button", 1)[1].split("\ndef ", 1)[0]
    assert "st.iframe(" in fn
    assert "components.v1" not in source
    assert "components.html" not in source
