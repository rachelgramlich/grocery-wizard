"""Extract plain text from recipe ingredient files (PDF, JPEG, PNG) for editing."""

from __future__ import annotations

import io
import re
from pathlib import Path

__all__ = [
    "SUPPORTED_MIME_TYPES",
    "extension_from_mime",
    "ingredient_text_from_upload",
    "normalize_extracted_lines",
]


SUPPORTED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)


def extension_from_mime(mime: str) -> str:
    """Return a filename suffix for Streamlit ``type`` (lowercase, with dot)."""
    m = mime.split(";")[0].strip().lower()
    if m == "application/pdf":
        return ".pdf"
    if m in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if m == "image/png":
        return ".png"
    if m == "image/webp":
        return ".webp"
    return ""


def _lines_from_pdf(data: bytes) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw in text.splitlines():
            stripped = raw.strip()
            if stripped:
                lines.append(stripped)
    return lines


def _lines_from_image(data: bytes) -> list[str]:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover — optional system dep
        raise RuntimeError(
            "Image text extraction needs pytesseract and a Tesseract OCR engine. "
            "Install tesseract-ocr on the system, then pip install pytesseract."
        ) from exc
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    text = pytesseract.image_to_string(image) or ""
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped:
            lines.append(stripped)
    return lines


def normalize_extracted_lines(lines: list[str]) -> str:
    """Collapse OCR noise to one-ingredient-per-line text for the Notion field."""
    cleaned: list[str] = []
    bullet_re = re.compile(r"^[\s•\-\*·]+")

    for raw_line in lines:
        stripped_line = bullet_re.sub("", raw_line).strip()
        if not stripped_line:
            continue
        if re.fullmatch(r"ingredients?:?", stripped_line, re.IGNORECASE):
            continue
        cleaned.append(stripped_line)

    return "\n".join(cleaned)


def ingredient_text_from_upload(data: bytes, mime_type: str) -> str:
    """Return multi-line ingredient text from raw file bytes."""
    m = mime_type.split(";")[0].strip().lower()
    if m == "application/pdf":
        lines = _lines_from_pdf(data)
    elif m in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        lines = _lines_from_image(data)
    else:
        raise ValueError(f"Unsupported type: {mime_type!r}")

    return normalize_extracted_lines(lines)


def ingredient_text_from_path(path: Path) -> str:
    """Load a file from disk (tests, CLI). MIME from suffix."""
    suffix = path.suffix.lower()
    data = path.read_bytes()
    if suffix == ".pdf":
        return normalize_extracted_lines(_lines_from_pdf(data))
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return normalize_extracted_lines(_lines_from_image(data))
    raise ValueError(f"Unsupported file extension: {suffix!r}")
