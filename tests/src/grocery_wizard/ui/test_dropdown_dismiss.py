"""Touch dismissal for popovers, select, and multiselect menus (issue #440)."""

from __future__ import annotations

from ui_source import APP_PATH

from src.grocery_wizard.ui.dropdown_dismiss import (
    DROPDOWN_DISMISS_JS,
    dropdown_dismiss_iframe_html,
)
from src.grocery_wizard.ui.theme import app_theme_css


def _js() -> str:
    return DROPDOWN_DISMISS_JS.read_text(encoding="utf-8")


def test_dismiss_script_listens_for_touch_taps_not_click() -> None:
    js = _js()
    for event_name in ("pointerdown", "touchstart", "pointerup", "touchend"):
        assert f'"{event_name}"' in js
    assert "capture: true" in js
    assert "TAP_SLOP_PX" in js


def test_dismiss_script_closes_open_comboboxes_outside_the_tap() -> None:
    js = _js()
    assert '[role="combobox"][aria-expanded="true"]' in js
    assert "combobox.blur()" in js
    assert '"Escape"' in js
    assert "stSelectboxVirtualDropdown" in js
    assert "stMultiSelectDropdown" in js


def test_dismiss_script_closes_open_popovers_with_an_outside_click() -> None:
    js = _js()
    assert '[data-testid="stPopoverButton"][aria-expanded="true"]' in js
    assert "stPopoverBody" in js
    assert 'new MouseEvent("click"' in js


def test_dismiss_script_blurs_after_touch_option_pick_in_single_select() -> None:
    js = _js()
    assert 'event.pointerType !== "touch"' in js
    assert '[role="option"]' in js


def test_dismiss_script_exposes_install_marker() -> None:
    js = _js()
    assert "window.__gwDropdownDismiss" in js
    assert "data-gw-dropdown-dismiss" in js


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
