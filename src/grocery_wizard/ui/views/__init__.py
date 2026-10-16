"""Streamlit page bodies and top-level page navigation (segmented control)."""

from __future__ import annotations

from typing import Final

from src.grocery_wizard.ui.ids import (
    PAGE_SLUG_ADD,
    PAGE_SLUG_MAINTENANCE,
    PAGE_SLUG_PANTRY,
    PAGE_SLUG_WEEKLY,
)

PAGE_LABEL_WEEKLY: Final = "Create weekly plan"
PAGE_LABEL_ADD: Final = "Add Recipe"
PAGE_LABEL_PANTRY: Final = "Pantry & recurring"
PAGE_LABEL_MAINTENANCE: Final = "Recipe maintenance"

PAGE_PICKER_LABELS: Final = (
    PAGE_LABEL_WEEKLY,
    PAGE_LABEL_ADD,
    PAGE_LABEL_PANTRY,
    PAGE_LABEL_MAINTENANCE,
)

PAGE_SLUG_BY_LABEL: Final[dict[str, str]] = {
    PAGE_LABEL_WEEKLY: PAGE_SLUG_WEEKLY,
    PAGE_LABEL_ADD: PAGE_SLUG_ADD,
    PAGE_LABEL_PANTRY: PAGE_SLUG_PANTRY,
    PAGE_LABEL_MAINTENANCE: PAGE_SLUG_MAINTENANCE,
}

PAGE_LABEL_BY_SLUG: Final[dict[str, str]] = {
    slug: label for label, slug in PAGE_SLUG_BY_LABEL.items()
}


def page_slug_for_label(label: str) -> str:
    return PAGE_SLUG_BY_LABEL.get(label, "unknown")


def page_label_for_slug(slug: str) -> str | None:
    return PAGE_LABEL_BY_SLUG.get(slug)
