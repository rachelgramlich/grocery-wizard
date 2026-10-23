"""Touch dismissal for select / multiselect menus (issue #440)."""

from __future__ import annotations

from ui_source import APP_PATH

from src.grocery_wizard.ui.dropdown_dismiss import (
    DROPDOWN_DISMISS_JS,
    dropdown_dismiss_iframe_html,
)
from src.grocery_wizard.ui.theme import app_theme_css


def test_dismiss_script_blurs_open_combobox_on_outside_press() -> None:
    js = DROPDOWN_DISMISS_JS.read_text(encoding="utf-8")
    assert '"pointerdown"' in js
    assert 'getAttribute("aria-expanded") === "true"' in js
    assert "combobox.blur()" in js
    assert "stSelectboxVirtualDropdown" in js
    assert "stMultiSelectDropdown" in js


def test_dismiss_script_blurs_after_touch_option_pick_in_single_select() -> None:
    js = DROPDOWN_DISMISS_JS.read_text(encoding="utf-8")
    assert 'event.pointerType !== "touch"' in js
    assert '[role="option"]' in js


def test_iframe_installs_script_into_parent_document() -> None:
    html = dropdown_dismiss_iframe_html()
    assert "window.parent.document" in html
    assert "__gwDropdownDismiss" in html


def test_app_installs_dropdown_dismiss() -> None:
    assert "install_dropdown_dismiss()" in APP_PATH.read_text(encoding="utf-8")


def test_mobile_css_caps_dropdown_menu_height() -> None:
    css = app_theme_css()
    mobile = css.split("@media (max-width: 768px)", 1)[1]
    assert '[data-testid="stSelectboxVirtualDropdown"]' in mobile
    assert '[data-testid="stMultiSelectDropdown"]' in mobile
    assert "max-height: min(40vh, 18rem)" in mobile
