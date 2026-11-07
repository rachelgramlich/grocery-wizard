"""Extract plain-text ingredient lines from a PDF or raster image file.

Uses **PyMuPDF** for PDF text and **pytesseract** for images (and PDFs where embedded
text is empty). Lines are filtered with the same heuristics as URL scrapes
(``looks_like_ingredient_line``) plus instruction/metadata filters from the
ingredients pipeline.

**HEIC / HEIF** (common iPhone exports): requires ``pillow-heif``; registered on first decode.

OCR typo repair uses ``recipes/data/ocr_line_fixes.json`` (regex ``match`` → ``replace``).
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
from src.grocery_wizard.recipes.ocr_line_fixes import apply_ocr_line_fixes
from src.grocery_wizard.recipes.scraper import ingredients_to_text, looks_like_ingredient_line

_PDF_SIG = b"%PDF-"
_JPEG_SOI = b"\xff\xd8\xff"
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF = b"RIFF"
_HEIF_REGISTERED = False


def _register_heif_opener() -> None:
    """Register HEIF/HEIC decode with Pillow (optional dependency ``pillow-heif``)."""
    global _HEIF_REGISTERED  # noqa: PLW0603
    if _HEIF_REGISTERED:
        return
    try:
        import pillow_heif
    except ImportError:
        return
    pillow_heif.register_heif_opener()
    _HEIF_REGISTERED = True


def _is_heif_brand(data: bytes) -> bool:
    """ISO BMFF ``ftyp`` box: HEIC/HEIF/AVIF family brands in the first ~32 bytes."""
    if len(data) < 12 or data[4:8] != b"ftyp":
        return False
    head = data[8:32]
    return any(
        marker in head
        for marker in (b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1", b"avis", b"avif")
    )


_INGREDIENTS_HEADING = re.compile(r"^\s*ingredients\b", re.IGNORECASE)
_SECTION_HEADING = re.compile(
    r"^\s*(ingredients|for the|make the|to (?:make|serve)|garnish|topping|"
    r"frosting|dressing|sauce|glaze|filling|crust|batter|dough)\b",
    re.IGNORECASE,
)

# Magazine / card headers (not grocery lines).
_MAGAZINE_PIPE_DATE = re.compile(
    r"^.+\|\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*$",
    re.IGNORECASE,
)

# Phrases common on scanned recipe cards that are steps, not ingredients.
_OCR_INSTRUCTION_HINT = re.compile(
    r"\b(?:"
    r"into\s+(?:a\s+)?(?:medium|large|small)\s+bowl|"
    r"into\s+(?:the\s+)?(?:bundt|tube)\s+pan|"
    r"using\s+electric\s+mixer|"
    r"beat\s+until|gradually\s+beat|gradually\s+add|"
    r"fold\s+(?:apple|in|the\b)|"
    r"melt\s+butter|heavy\s+small\s+skillet|"
    r"continue\s+to\s+whisk|whisk\s+in|"
    r"turn\s+cake\s+out|"
    r"pour\s+remaining|"
    r"let\s+stand\s+until|"
    r"cover\s+with\s+cake\s+dome|"
    r"transfer\s+\d+\s+tablespoons|"
    r"set\s+pan\s+aside"
    r")\b",
    re.IGNORECASE,
)

# OCR often drops the space in ``1½`` → ``11/2``.
_GLUED_MIXED_FRACTION = re.compile(r"\b(1|2|3|4)(1|2|3|4)/(2|3|4)\b")

# OCR paragraphs split mid-sentence — a new sentence after a period is almost always a step.
_MULTI_SENTENCE = re.compile(r"\.\s+[A-Z]")

_OCR_LEADING_STEP = re.compile(
    r"^(?:preheat|bake\s+|place\s+|spray\s+|sift\s+|transfer\s+cake|whisk\s+|melt\s+|fold\s+|pour\s+|"
    r"combine\s+1\s+cup\s+brown|let\s+cake\s+cool|cool\s+cake)\b",
    re.IGNORECASE,
)

# Two-token OCR junk (e.g. ``11 oe`` next to a real quantity line).
_OCR_JUNK_TWO_TOKEN = re.compile(r"^\d{1,2}\s+[a-z]{2}\s*$", re.IGNORECASE)


class FileIngredientsError(Exception):
    """Uploaded file could not be read or yielded no ingredient-like lines."""


def guess_mime_type(data: bytes) -> str:
    """Return a coarse MIME type for ``data`` (pdf, jpeg, png, webp, heic) or octet-stream."""
    if len(data) >= 5 and data.startswith(_PDF_SIG):
        return "application/pdf"
    if len(data) >= 3 and data.startswith(_JPEG_SOI):
        return "image/jpeg"
    if len(data) >= 8 and data.startswith(_PNG_SIG):
        return "image/png"
    if len(data) >= 12 and data.startswith(_WEBP_RIFF) and data[8:12] == b"WEBP":
        return "image/webp"
    if _is_heif_brand(data):
        return "image/heic"
    return "application/octet-stream"


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError):
        return False
    return True


def _ocr_image_bytes(data: bytes) -> str:
    _register_heif_opener()
    try:
        image = Image.open(io.BytesIO(data))
    except OSError as exc:
        raise FileIngredientsError(
            "Could not open image bytes. For HEIC/HEIF, install pillow-heif (included in app deps)."
        ) from exc
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    fmt = (image.format or "").upper()
    if fmt in {"HEIF", "HEIC", "AVIF"} or "Heif" in type(image).__name__:
        png_buf = io.BytesIO()
        image.save(png_buf, format="PNG")
        png_buf.seek(0)
        image = Image.open(png_buf)
    return pytesseract.image_to_string(image)


def _pdf_text_pages(doc: fitz.Document) -> Iterable[str]:
    for page in doc:
        yield page.get_text()


def _pdf_ocr_page(page: fitz.Page) -> str:
    pix = page.get_pixmap(dpi=200, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(image)


_OCR_LEADING_PIPE_AT_CUP = re.compile(r"^\|\s*@cups\b", re.IGNORECASE)


def _normalize_ocr_leader_typos(line: str) -> str:
    """Repair leading OCR junk before quantity (e.g. ``| @cups`` → ``1 cup``)."""
    stripped = line.strip()
    if _OCR_LEADING_PIPE_AT_CUP.match(stripped):
        return _OCR_LEADING_PIPE_AT_CUP.sub("1 cup", stripped, count=1)
    return stripped


def _normalize_ocr_fraction_glitch(line: str) -> str:
    """Turn ``11/2 cups`` into ``1 1/2 cups`` when OCR drops a space."""

    def repl(match: re.Match[str]) -> str:
        whole, num, denom = match.group(1), match.group(2), match.group(3)
        return f"{whole} {num}/{denom}"

    return _GLUED_MIXED_FRACTION.sub(repl, line)


def _is_ocr_magazine_junk(line: str) -> bool:
    if _MAGAZINE_PIPE_DATE.match(line.strip()):
        return True
    return bool(re.search(r"\bbon\s+app[eé]tit\b", line, re.IGNORECASE) and "|" in line)


def _is_lowercase_comma_instruction(line: str) -> bool:
    """Lines like ``brown sugar, vegetable oil, 1 cup sugar, ...`` (method, not a single item)."""
    stripped = line.strip()
    if not stripped or stripped[0].isupper() or stripped[0].isdigit():
        return False
    if stripped.count(",") < 2:
        return False
    return bool(re.search(r",\s+vegetable\s+oil\b", stripped, re.IGNORECASE))


def _is_ocr_two_token_garbage(line: str) -> bool:
    stripped = line.strip()
    if not _OCR_JUNK_TWO_TOKEN.match(stripped):
        return False
    second = stripped.split()[-1].lower()
    return second not in {"oz", "lb", "ml", "g", "kg"}


def _keep_line_for_file_extraction(line: str) -> bool:
    """Stricter than URL scrape: drop OCR'd method sentences that still look like amounts."""
    if not looks_like_ingredient_line(line, max_length=130):
        return False
    if is_directive(line):
        return False
    if is_metadata_line(line) or is_recipe_step_line(line):
        return False
    if _is_ocr_magazine_junk(line):
        return False
    stripped = line.strip()
    if is_instruction_line(stripped) and not looks_like_ingredient_line(stripped, max_length=130):
        return False
    if _OCR_INSTRUCTION_HINT.search(stripped):
        return False
    if _is_lowercase_comma_instruction(stripped):
        return False
    if _is_ocr_two_token_garbage(stripped):
        return False
    if len(stripped) > 110:
        return False
    if stripped.endswith("."):
        return False
    return not (bool(_MULTI_SENTENCE.search(stripped)) or bool(_OCR_LEADING_STEP.match(stripped)))


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

    def collect(source: list[str], block_start: int) -> list[str]:
        out: list[str] = []
        in_block = block_start > 0
        for raw_line in source[block_start:] if in_block else source:
            line = _normalize_ocr_fraction_glitch(
                apply_ocr_line_fixes(_normalize_ocr_leader_typos(raw_line))
            )
            if (
                in_block
                and _SECTION_HEADING.match(line)
                and not looks_like_ingredient_line(line, max_length=130)
            ):
                break
            if not _keep_line_for_file_extraction(line):
                continue
            out.append(line)
        return out

    return collect(stripped, start)


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
    elif resolved in {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
    }:
        ingredients = _extract_from_image(data)
    else:
        raise FileIngredientsError(
            f"Unsupported file type ({resolved or 'unknown'}). "
            "Use PDF, JPEG, PNG, WebP, or HEIC/HEIF."
        )

    if not ingredients:
        raise FileIngredientsError(
            "No ingredient lines found. Try a clearer scan or paste ingredients manually."
        )
    return ingredients


def ingredients_text_from_file_bytes(data: bytes, *, mime_type: str | None = None) -> str:
    """Same as ``extract_ingredients_from_file_bytes`` but returns newline-joined text."""
    return ingredients_to_text(extract_ingredients_from_file_bytes(data, mime_type=mime_type))
