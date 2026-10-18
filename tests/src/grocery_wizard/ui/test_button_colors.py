"""Every button widget must render with an approved, readable color combo.

Two failure modes this guards against (both shipped once as dark label on dark fill):

1. A CSS rule gives a button a fill but a generic rule (``.stApp p``) gives its label
   the page text color. Streamlit renders different DOM per widget (``st.button`` vs
   ``st.form_submit_button`` vs ``st.link_button``), so a rule written for one widget
   silently misses the others.
2. Someone adds a new button widget or ``type=`` that no rule targets.

The approved combos live in ``theme.approved_button_colors``; the cascade is resolved by
``css_cascade`` against hand-built copies of Streamlit's button DOM.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

import pytest
from css_cascade import Element, Stylesheet

from src.grocery_wizard.ui.theme import (
    APP_THEME_STATIC_CSS,
    GW_THEME,
    MIN_CONTRAST_RATIO_AA,
    approved_button_colors,
    contrast_ratio,
)
from tests.repo_paths import UI_SRC_ROOT

_APPROVED = approved_button_colors(GW_THEME)

# Widgets that render a button-like control. Using one that is not in
# ``_BUTTON_DOM_VARIANTS`` fails ``test_ui_only_uses_covered_button_widgets``.
_BUTTON_WIDGETS = frozenset(
    {
        "button",
        "form_submit_button",
        "download_button",
        "link_button",
        "popover",
        "pills",
        "segmented_control",
        "feedback",
    }
)
_ALLOWED_TYPES = frozenset(_APPROVED)

# Button-like widgets left on Streamlit's own styling, with the reason that is safe.
# Verified in a browser: labels use --gw-text on the page bg / a translucent accent tint
# (both covered by the "body text on page" contrast pair).
_STREAMLIT_STYLED_WIDGETS = frozenset({"segmented_control"})


@dataclass(frozen=True, slots=True)
class ButtonDom:
    """One button widget variant and the combo it must render with."""

    widget: str
    kind: str
    expected_kind: str
    root_class: str
    root_testid: str
    control_tag: str
    control_testid: str

    @property
    def id(self) -> str:
        return f"{self.widget}-{self.kind}"

    def label_elements(self) -> list[Element]:
        """Control plus the text/icon nodes Streamlit renders inside it."""
        app = Element("div", ("stApp",), {"data-testid": "stApp"})
        block = app.child("div", attrs={"data-testid": "stVerticalBlock"})
        root = block.child(
            "div", classes=(self.root_class,), attrs={"data-testid": self.root_testid}
        )
        control = root.child(self.control_tag, attrs={"data-testid": self.control_testid})
        markdown = control.child("div", attrs={"data-testid": "stMarkdownContainer"})
        return [
            control,
            markdown,
            markdown.child("p"),
            control.child("span", attrs={"data-testid": "stIconMaterial"}),
        ]


def _variants() -> list[ButtonDom]:
    variants: list[ButtonDom] = []
    for kind in ("primary", "secondary"):
        variants += [
            ButtonDom(
                "button", kind, kind, "stButton", "stButton", "button", f"stBaseButton-{kind}"
            ),
            ButtonDom(
                "form_submit_button",
                kind,
                kind,
                "stFormSubmitButton",
                "stFormSubmitButton",
                "button",
                f"stBaseButton-{kind}FormSubmit",
            ),
            # Download buttons are deliberately always primary (see app_theme.css).
            ButtonDom(
                "download_button",
                kind,
                "primary",
                "stDownloadButton",
                "stDownloadButton",
                "button",
                f"stBaseButton-{kind}",
            ),
            ButtonDom(
                "link_button",
                kind,
                kind,
                "stLinkButton",
                "stLinkButton",
                "a",
                f"stBaseLinkButton-{kind}",
            ),
        ]
    variants.append(
        ButtonDom(
            "popover", "secondary", "secondary", "stPopover", "stPopover", "button",
            "stPopoverButton",
        )
    )  # fmt: skip
    return variants


_BUTTON_DOM_VARIANTS = _variants()
_COVERED_WIDGETS = frozenset(variant.widget for variant in _BUTTON_DOM_VARIANTS)


@pytest.fixture(scope="module")
def stylesheet() -> Stylesheet:
    return Stylesheet(APP_THEME_STATIC_CSS.read_text(encoding="utf-8"))


@pytest.mark.parametrize("variant", _BUTTON_DOM_VARIANTS, ids=lambda v: v.id)
def test_button_renders_with_approved_color_combo(
    stylesheet: Stylesheet, variant: ButtonDom
) -> None:
    expected_fg, expected_bg = (c.lower() for c in _APPROVED[variant.expected_kind])
    control, *labels = variant.label_elements()

    fill = stylesheet.computed(control, "background-color")
    assert fill is not None, (
        f"{variant.id}: app_theme.css never sets a fill for {control.path()}; "
        "add it to the button rules instead of relying on Streamlit defaults"
    )
    assert fill == expected_bg, (
        f"{variant.id}: fill {fill} is not the approved {variant.expected_kind} fill {expected_bg}"
    )

    for element in (control, *labels):
        text = stylesheet.computed(element, "-webkit-text-fill-color") or stylesheet.computed(
            element, "color"
        )
        assert text is not None, f"{variant.id}: no label color for {element.path()}"
        assert text == expected_fg, (
            f"{variant.id}: label at {element.path()} renders {text} on {fill}; "
            f"approved combo is {expected_fg} on {expected_bg}"
        )
        assert contrast_ratio(text, fill) >= MIN_CONTRAST_RATIO_AA


@pytest.mark.parametrize(("kind", "combo"), sorted(_APPROVED.items()))
def test_approved_combos_are_readably_different(kind: str, combo: tuple[str, str]) -> None:
    foreground, background = combo
    ratio = contrast_ratio(foreground, background)
    assert ratio >= MIN_CONTRAST_RATIO_AA, f"{kind}: {ratio:.2f} for {foreground} on {background}"


def test_primary_and_secondary_buttons_do_not_share_a_combo() -> None:
    assert _APPROVED["primary"] != _APPROVED["secondary"]
    assert _APPROVED["primary"][1] != _APPROVED["secondary"][1]


def _streamlit_calls() -> list[tuple[str, str, int, ast.Call]]:
    return [
        (str(path.relative_to(UI_SRC_ROOT)), node.func.attr, node.lineno, node)
        for path in sorted(UI_SRC_ROOT.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
        and node.func.attr in _BUTTON_WIDGETS
    ]


def test_ui_only_uses_covered_button_widgets() -> None:
    uncovered = [
        f"{path}:{line} st.{widget}"
        for path, widget, line, _ in _streamlit_calls()
        if widget not in _COVERED_WIDGETS | _STREAMLIT_STYLED_WIDGETS
    ]
    assert not uncovered, (
        "Button-like widgets without approved colors. Add CSS in app_theme.css and a "
        f"ButtonDom variant in this test first: {uncovered}"
    )


def _type_values(node: ast.expr) -> list[object]:
    """Possible values of a ``type=`` expression; non-literal branches become ``None``."""
    if isinstance(node, ast.IfExp):
        return [*_type_values(node.body), *_type_values(node.orelse)]
    if isinstance(node, ast.Constant):
        return [node.value]
    return [None]


def test_ui_button_types_are_literal_and_approved() -> None:
    bad = []
    for path, widget, line, call in _streamlit_calls():
        for keyword in call.keywords:
            if keyword.arg != "type":
                continue
            values = _type_values(keyword.value)
            if not set(values) <= _ALLOWED_TYPES:
                bad.append(f"{path}:{line} st.{widget}(type=...) -> {values}")
    assert not bad, f"Button type must be a literal in {sorted(_ALLOWED_TYPES)}: {bad}"
