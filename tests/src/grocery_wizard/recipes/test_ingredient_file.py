"""Tests for ingredient text extraction from PDF uploads."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from src.grocery_wizard.recipes.ingredient_file import (
    ingredient_text_from_path,
    normalize_extracted_lines,
)


@pytest.fixture
def minimal_pdf(tmp_path: Path) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    path = tmp_path / "recipe.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_normalize_extracted_lines_strips_heading_and_bullets() -> None:
    raw = [
        "Ingredients:",
        "• 2 cups flour",
        "- 1 egg",
    ]
    assert normalize_extracted_lines(raw) == "2 cups flour\n1 egg"


def test_ingredient_text_from_path_accepts_blank_pdf(minimal_pdf: Path) -> None:
    # pypdf blank pages produce no text — still a valid smoke path for PDF wiring.
    assert ingredient_text_from_path(minimal_pdf) == ""
