"""Regression hooks for heading / expander typography (issue #222)."""

from __future__ import annotations

from src.grocery_wizard.ui.theme import app_theme_css

_REQUIRED_TYPOGRAPHY_FRAGMENTS = (
    "--gw-heading-section-size",
    "--gw-heading-step-size",
    "--gw-heading-subsection-color",
    "--gw-heading-expander-color",
    "--gw-heading-expander-weight",
    '[data-testid="stTitle"] [data-testid="stMarkdownContainer"] h1',
    "font-size: revert",
    '[data-testid="stSubheader"]',
    '[data-testid="stMarkdownContainer"] h3',
    '[data-testid="stMarkdownContainer"] h4',
    "p:has(> strong:only-child)",
    "p.gw-meal-slot-label",
    '[data-testid="stExpander"] summary',
)


def test_app_theme_css_defines_header_hierarchy_scale() -> None:
    css = app_theme_css()
    missing = [frag for frag in _REQUIRED_TYPOGRAPHY_FRAGMENTS if frag not in css]
    assert not missing, f"app_theme_css missing typography hooks: {missing}"


def test_markdown_heading_rules_do_not_shrink_page_title() -> None:
    css = app_theme_css()
    assert '.stApp [data-testid="stMarkdownContainer"] h1,' not in css
    assert '.stApp [data-testid="stMarkdownContainer"] h2,' not in css
    assert 'font-size: revert' in css


def test_heading_size_tokens_are_monotonic() -> None:
    css = app_theme_css()

    def _rem(token: str) -> float:
        needle = f"{token}: "
        start = css.index(needle) + len(needle)
        end = css.index("rem", start)
        return float(css[start:end])

    section = _rem("--gw-heading-section-size")
    step = _rem("--gw-heading-step-size")
    subsection = _rem("--gw-heading-subsection-size")
    expander = _rem("--gw-heading-expander-size")
    assert section >= step >= subsection >= expander
