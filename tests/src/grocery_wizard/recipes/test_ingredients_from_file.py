"""Tests for PDF / image ingredient extraction."""

from __future__ import annotations

import io

import fitz
import pillow_heif
import pytest
from PIL import Image, ImageDraw, ImageFont

from src.grocery_wizard.recipes.ingredients_from_file import (
    FileIngredientsError,
    extract_ingredients_from_file_bytes,
    guess_mime_type,
)
from src.grocery_wizard.recipes.ocr_line_fixes import apply_ocr_line_fixes


def _build_simple_pdf_with_text(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=200, height=400)
    page.insert_text((72, 72), text, fontsize=12)
    out = doc.tobytes()
    doc.close()
    return out


def test_guess_mime_type_sniffs_signatures() -> None:
    assert guess_mime_type(b"%PDF-1.4\n") == "application/pdf"
    assert guess_mime_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert guess_mime_type(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert guess_mime_type(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00") == "image/heic"


def test_ocr_line_fixes_json_replaces_garbled_brown_sugar() -> None:
    assert apply_ocr_line_fixes("10 Oram Bune") == "1 cup packed brown sugar"
    assert apply_ocr_line_fixes("10 Oram Bue") == "1 cup packed brown sugar"


def test_extract_from_pdf_text_layer() -> None:
    body = """Chocolate Cake

Yield: Makes 12 servings

Ingredients
1 cup flour
2 tbsp cocoa
1 tsp vanilla
Instructions
Bake at 350°F."""
    pdf_bytes = _build_simple_pdf_with_text(body)
    lines = extract_ingredients_from_file_bytes(pdf_bytes, mime_type="application/pdf")
    assert "1 cup flour" in lines
    assert "2 tbsp cocoa" in lines
    assert "1 tsp vanilla" in lines
    assert all("Yield" not in ln for ln in lines)


def test_ocr_glued_fraction_from_pdf() -> None:
    pdf_bytes = _build_simple_pdf_with_text("11/2 cups vegetable oil")
    lines = extract_ingredients_from_file_bytes(pdf_bytes, mime_type="application/pdf")
    assert any("1 1/2 cups vegetable oil" in ln for ln in lines)


def test_ocr_pipe_at_cups_and_oram_give_two_brown_sugar_lines() -> None:
    from src.grocery_wizard.recipes.ingredients_from_file import _ingredient_block_from_lines

    lines = _ingredient_block_from_lines(
        [
            "Ingredients",
            "| @cups (packed) golden brown sugar",
            "10 Oram Bue",
            "1 cup sugar",
        ]
    )
    brown = [ln for ln in lines if "brown sugar" in ln.lower()]
    assert len(brown) == 2
    assert any("golden" in ln.lower() for ln in brown)
    assert "1 cup sugar" in lines


def test_extract_requires_ingredient_like_lines() -> None:
    pdf_bytes = _build_simple_pdf_with_text("Hello world\nNo recipe here.")
    with pytest.raises(FileIngredientsError, match="No ingredient lines"):
        extract_ingredients_from_file_bytes(pdf_bytes, mime_type="application/pdf")


def test_unsupported_mime_raises() -> None:
    with pytest.raises(FileIngredientsError, match="Unsupported file type"):
        extract_ingredients_from_file_bytes(b"not a real file", mime_type="text/plain")


def test_extract_from_jpeg_ocr_when_tesseract_present() -> None:
    pytesseract = pytest.importorskip("pytesseract")
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError):
        pytest.skip("Tesseract OCR not installed")

    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 80), "1 cup flour", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    data = buf.getvalue()

    lines = extract_ingredients_from_file_bytes(data, mime_type="image/jpeg")
    joined = " ".join(lines).lower()
    assert "flour" in joined
    assert any("cup" in ln.lower() for ln in lines)


def test_extract_from_heic_when_pillow_heif_and_tesseract_present() -> None:
    pytesseract = pytest.importorskip("pytesseract")
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError):
        pytest.skip("Tesseract OCR not installed")

    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 80), "2 tbsp sugar", fill="black", font=font)
    out = io.BytesIO()
    pillow_heif.encode("RGB", img.size, img.tobytes(), out)
    data = out.getvalue()

    lines = extract_ingredients_from_file_bytes(data, mime_type="image/heic")
    joined = " ".join(lines).lower()
    assert "sugar" in joined
