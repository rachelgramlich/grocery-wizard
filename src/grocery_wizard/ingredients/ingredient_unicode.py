"""Unicode dash/fraction normalization for ingredient lines (no parsed/normalize coupling)."""

from __future__ import annotations

from src.grocery_wizard.ingredients._patterns import (
    _UNICODE_DASHES,
    _UNICODE_FRACTIONS,
)


def _normalize_unicode_read(text: str) -> str:
    """Unicode dashes/fractions only (grocery read / parse stored lines)."""
    for dash in _UNICODE_DASHES:
        text = text.replace(dash, "-")
    for char, replacement in _UNICODE_FRACTIONS.items():
        text = text.replace(char, replacement)
    return text


def _normalize_unicode(text: str) -> str:
    return _normalize_unicode_read(text)


def _normalize_unicode_for_storage(text: str) -> str:
    """Storage pipeline: also strip dual measures (``cup/240 grams``), packed, typos, etc."""
    from src.grocery_wizard.ingredients._cleaning import normalize_measurement_text

    return normalize_measurement_text(_normalize_unicode_read(text))
