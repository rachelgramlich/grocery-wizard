"""Extract plain-text ingredient lines from a PDF or raster image file.

Uses **PyMuPDF** for PDF text and **pytesseract** for images (and PDFs where embedded
text is empty). Lines are filtered with the same heuristics as URL scrapes
(``looks_like_ingredient_line``) plus instruction/metadata filters from the
ingredients pipeline.
"""

from __future__ import annotations

__all__ = [
    "FileIngredientsError",
    "extract_ingredients_from_file_bytes",
    "guess_mime_type",
    "ingredients_text_from_file_bytes",
]

import io
import re
from collections.abc import Iterable

import fitz
import pytesseract
from PIL import Image

from src.grocery_wizard.ingredients.normalize import (
    is_instruction_line,
    is_metadata_line,
    is_recipe_step_line,
)
from src.grocery_wizard.ingredients.sync import is_directive
from src.grocery_wizard.recipes.scraper import ingredients_to_text, looks_like_ingredient_line

_PDF_SIG = b"%PDF-"
_JPEG_SOI = b"\xff\xd8\xff"
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF = b"RIFF"

_INGREDIENTS_HEADING = re.compile(r"^\s*ingredients\b", re.IGNORECASE)
_SECTION_HEADING = re.compile(
    r"^\s*(ingredients|for the|make the|to (?:make|serve)|garnish|topping|"
    r"frosting|dressing|sauce|glaze|filling|crust|batter|dough)\b",
    re.IGNORECASE,
)


class FileIngredientsError(Exception):
    """Uploaded file could not be read or yielded no ingredient-like lines."""


def guess_mime_type(data: bytes) -> str:
    """Return a coarse MIME type for ``data`` (pdf, jpeg, png, webp) or application/octet-stream."""
    if len(data) >= 5 and data.startswith(_PDF_SIG):
        return "application/pdf"
    if len(data) >= 3 and data.startswith(_JPEG_SOI):
        return "image/jpeg"
    if len(data) >= 8 and data.startswith(_PNG_SIG):
        return "image/png"
    if len(data) >= 12 and data.startswith(_WEBP_RIFF) and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError):
        return False
    return True


def _ocr_image_bytes(data: bytes) -> str:
    image = Image.open(io.BytesIO(data))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    return pytesseract.image_to_string(image)


def _pdf_text_pages(doc: fitz.Document) -> Iterable[str]:
    for page in doc:
        yield page.get_text()


def _pdf_ocr_page(page: fitz.Page) -> str:
    pix = page.get_pixmap(dpi=200, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(image)


def _ingredient_block_from_lines(lines: list[str]) -> list[str]:
    """From flat text lines, keep ingredient-like lines; optionally start at 'Ingredients'."""
    stripped = [ln.strip() for ln in lines if ln.strip()]
    if not stripped:
        return []

    start = 0
    for i, line in enumerate(stripped):
        if _INGREDIENTS_HEADING.match(line):
            start = i + 1
            break

    out: list[str] = []
    in_block = start > 0
    for line in stripped[start:] if in_block else stripped:
        if in_block and _SECTION_HEADING.match(line) and not looks_like_ingredient_line(line):
            break
        if not looks_like_ingredient_line(line):
            continue
        if is_directive(line) or is_metadata_line(line) or is_instruction_line(line):
            continue
        if is_recipe_step_line(line):
            continue
        out.append(line)

    if out:
        return out

    for line in stripped:
        if not looks_like_ingredient_line(line):
            continue
        if is_directive(line) or is_metadata_line(line) or is_instruction_line(line):
            continue
        if is_recipe_step_line(line):
            continue
        out.append(line)
    return out


def _lines_from_text(text: str) -> list[str]:
    return [ln.rstrip() for ln in re.split(r"[\n\r\f]+", text) if ln.strip()]


def _extract_from_pdf(data: bytes) -> list[str]:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        parts = [page_text for page_text in _pdf_text_pages(doc) if page_text.strip()]
        combined = "\n".join(parts)
        lines = _lines_from_text(combined)
        picked = _ingredient_block_from_lines(lines)
        if picked:
            return picked

        if not _tesseract_available():
            return []

        ocr_parts = [_pdf_ocr_page(doc[page_index]) for page_index in range(len(doc))]
        ocr_lines = _lines_from_text("\n".join(ocr_parts))
        return _ingredient_block_from_lines(ocr_lines)
    finally:
        doc.close()


def _extract_from_image(data: bytes) -> list[str]:
    if not _tesseract_available():
        msg = (
            "Tesseract OCR is not installed or not on PATH. "
            "Install tesseract-ocr (e.g. apt install tesseract-ocr, brew install tesseract) "
            "to read ingredients from images."
        )
        raise FileIngredientsError(msg) from None
    text = _ocr_image_bytes(data)
    return _ingredient_block_from_lines(_lines_from_text(text))


def extract_ingredients_from_file_bytes(data: bytes, *, mime_type: str | None = None) -> list[str]:
    """Return ingredient lines extracted from file bytes (PDF or common image types).

    Raises:
        FileIngredientsError: Empty file, bad type, missing OCR, or no ingredient-like lines.
    """
    if not data:
        raise FileIngredientsError("Empty file.")

    resolved = (mime_type or "").strip().lower() or guess_mime_type(data)

    if resolved == "application/pdf":
        ingredients = _extract_from_pdf(data)
    elif resolved in {"image/jpeg", "image/png", "image/webp", "image/jpg"}:
        ingredients = _extract_from_image(data)
    else:
        raise FileIngredientsError(
            f"Unsupported file type ({resolved or 'unknown'}). Use PDF, JPEG, PNG, or WebP."
        )

    if not ingredients:
        raise FileIngredientsError(
            "No ingredient lines found. Try a clearer scan or paste ingredients manually."
        )
    return ingredients


def ingredients_text_from_file_bytes(data: bytes, *, mime_type: str | None = None) -> str:
    """Same as ``extract_ingredients_from_file_bytes`` but returns newline-joined text."""
    return ingredients_to_text(extract_ingredients_from_file_bytes(data, mime_type=mime_type))
