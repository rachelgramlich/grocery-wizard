"""Internal cleaning helpers for ingredient normalization."""

from __future__ import annotations

import re

from src.grocery_wizard.ingredients._patterns import (
    _CONJUNCTION_SPLIT_RE,
    _DIMENSION_PREP_SEGMENT_RE,
    _INSTRUCTION_ONLY_RE,
    _JUNK_ONLY_PHRASES,
    _PREP_ALTERNATIVE_RE,
    _PREP_WORDS,
    _QUANTITY_RE,
    _REMOVED_PREP_SEGMENT_RE,
    _SIZES,
    _STANDALONE_INGREDIENT_WORDS,
    _TRAILING_CLAUSE_RE,
    _UNICODE_DASHES,
    _UNICODE_FRACTIONS,
    _UNITS,
    _UNSPLIT_AND_PHRASES,
)

_PAREN_GROUP_RE = re.compile(r"\s*\([^()]*\)")


def strip_parenthetical_groups(text: str) -> str:
    """Remove ``(...)`` notes, including nested groups like ``( (optional))``."""
    previous = None
    while previous != text:
        previous = text
        text = _PAREN_GROUP_RE.sub("", text)
    open_index = text.find("(")
    if open_index != -1:
        text = text[:open_index]
    return text.replace(")", "").strip()


_ALT_MEASURE_UNITS = (
    r"grams?|g|kilograms?|kg|milliliters?|ml|liters?|ounces?|oz|pounds?|lbs?|"
    r"cups?|tablespoons?|teaspoons?"
)
# NYT dual measures: ``1 cup/240 grams`` and ``1/2 cup/4 ounces/113 grams``.
_ALT_MEASURE_RE = re.compile(
    rf"(?<=[A-Za-z])\s*/\s*(?:about\s+|approximately\s+)?\d+(?:\.\d+)?(?:\s+\d+/\d+)?"
    rf"\s*(?:{_ALT_MEASURE_UNITS})\b",
    re.IGNORECASE,
)
# ``2 packed cups spinach`` -> ``2 cups spinach`` (packing is prep, not an ingredient).
_PACKED_BEFORE_UNIT_RE = re.compile(
    r"(?P<qty>\d[\d/ ]*?)\s+(?:(?:lightly|loosely|firmly)\s+)?packed\s+"
    r"(?P<unit>cups?|tablespoons?|teaspoons?)\b",
    re.IGNORECASE,
)
# Scraped ``1½`` can arrive as ``11/2`` (also ``13/4``, ``11/3``).
_RUN_TOGETHER_MIXED_RE = re.compile(r"(?<![\d/.])(\d)(\d)/([2-9])(?=[\s-]|$)")
_QUANTITY_HEDGE_RE = re.compile(r"\b(?:scant|heaping|heaped|rounded)\s+", re.IGNORECASE)
_LEADING_APPROXIMATION_RE = re.compile(r"^(?:about|approximately|roughly)\s+(?=\d)", re.IGNORECASE)
_SIZE_ALTERNATIVE_RE = re.compile(
    r"\b(?:small|medium|large)\s+or\s+(?:small|medium|large)\b\s*",
    re.IGNORECASE,
)


def _split_run_together_mixed(match: re.Match[str]) -> str:
    whole, numerator, denominator = match.groups()
    if 1 <= int(numerator) < int(denominator):
        return f"{whole} {numerator}/{denominator}"
    return match.group(0)


def normalize_measurement_text(text: str) -> str:
    """Clean measurement quirks that otherwise leak into ingredient names."""
    text = _ALT_MEASURE_RE.sub("", text)
    text = _PACKED_BEFORE_UNIT_RE.sub(r"\g<qty> \g<unit>", text)
    text = _RUN_TOGETHER_MIXED_RE.sub(_split_run_together_mixed, text)
    text = _QUANTITY_HEDGE_RE.sub("", text)
    text = _LEADING_APPROXIMATION_RE.sub("", text.strip())
    return _SIZE_ALTERNATIVE_RE.sub("", text)


def mask_parenthetical_groups(text: str) -> str:
    """Blank out text inside parentheses, keeping string length and offsets."""
    depth = 0
    masked: list[str] = []
    for char in text:
        if char == "(":
            depth += 1
        if depth > 0:
            masked.append("_")
        else:
            masked.append(char)
        if char == ")" and depth > 0:
            depth -= 1
    return "".join(masked)


def _normalize_unicode_dashes(text: str) -> str:
    for dash in _UNICODE_DASHES:
        text = text.replace(dash, "-")
    for char, replacement in _UNICODE_FRACTIONS.items():
        text = text.replace(char, replacement)
    return text


def _normalize_unicode_fractions(text: str) -> str:
    for char, replacement in _UNICODE_FRACTIONS.items():
        text = text.replace(char, replacement)
    return text


_HERB_BEFORE_CITRUS_WEDGES_RE = re.compile(
    r"^(?P<left>.+\b(?:cilantro|parsley|mint|basil|dill))\s+"
    r"(?P<right>(?:lime|lemon)\s+wedges\b.*)$",
    re.IGNORECASE,
)


def _try_split_herb_before_citrus_wedges(text: str) -> tuple[str, str] | None:
    """``Chopped fresh cilantro lime wedges`` → cilantro phrase + citrus wedges."""
    match = _HERB_BEFORE_CITRUS_WEDGES_RE.match(text.strip())
    if match is None:
        return None
    left = match.group("left").strip()
    right = match.group("right").strip()
    if not left or not right:
        return None
    if not _looks_like_ingredient(left) or not _looks_like_ingredient(right):
        return None
    return left, right


def _split_compound_parts_recursive(text: str) -> list[str]:
    split = _try_split_on_conjunction(text)
    if split is None:
        split = _try_split_herb_before_citrus_wedges(text)
    if split is None:
        return [text]
    left, right = split
    return _split_compound_parts_recursive(left) + _split_compound_parts_recursive(right)


def _split_compound_parts(text: str) -> list[str]:
    return _split_compound_parts_recursive(text)


def _try_split_on_conjunction(text: str) -> tuple[str, str] | None:
    main = strip_parenthetical_groups(text).split(",")[0].strip()
    main = _TRAILING_CLAUSE_RE.sub("", main).strip().lower()
    if main in _UNSPLIT_AND_PHRASES:
        return None

    match = _CONJUNCTION_SPLIT_RE.search(mask_parenthetical_groups(text))
    if match is None:
        return None

    left = text[: match.start()].strip().rstrip(",")
    right = text[match.end() :].strip()
    if not left or not right:
        return None
    if _left_is_qty_plus_bare_color(left):
        return None
    if not _looks_like_ingredient(left) or not _looks_like_ingredient(right):
        return None
    return left, right


_COLOR_ADJECTIVES = frozenset(
    {"red", "yellow", "green", "white", "black", "orange", "purple", "golden"}
)


def _left_is_qty_plus_bare_color(left: str) -> bool:
    """True when *left* is only a quantity plus a color word (e.g. ``2 red``)."""
    text = left.strip().lower()
    text = _QUANTITY_RE.sub("", text, count=1).strip()
    words = text.split()
    while words and words[0] in _SIZES:
        words.pop(0)
    if not words:
        return False
    if len(words) == 1:
        return words[0] in _COLOR_ADJECTIVES
    return len(words) == 2 and words[0] in _COLOR_ADJECTIVES and words[1] in _COLOR_ADJECTIVES


def _looks_like_ingredient(part: str) -> bool:
    cleaned = strip_parenthetical_groups(part)
    cleaned = cleaned.split(",")[0].strip()
    cleaned = _TRAILING_CLAUSE_RE.sub("", cleaned).strip()
    if not cleaned:
        return False

    cleaned = _strip_leading_amount(cleaned)
    words = cleaned.lower().split()
    words = _strip_leading_tokens(words, _UNITS | _SIZES)
    while words and words[0] in _PREP_WORDS:
        words.pop(0)
    if not words:
        return False
    if len(words) >= 2:
        return True
    return len(words[0]) >= 4


def _split_leading_capitalized_ingredient(piece: str) -> list[str]:
    """``Salt fresh black pepper`` → ``Salt`` + ``fresh black pepper``."""
    words = piece.split(None, 1)
    if len(words) != 2:
        return [piece]
    first, rest = words
    if first[0].isupper() and rest[0].islower() and first.lower() in _STANDALONE_INGREDIENT_WORDS:
        return [first, rest]
    return [piece]


def _strip_leading_amount(text: str) -> str:
    """Remove leading quantities, including dual measures like ``1 cup/110 grams``."""
    text = re.sub(r"^\d+\s+\w+/\d+\s+\w+\s+", "", text, flags=re.IGNORECASE)
    return _QUANTITY_RE.sub("", text).strip()


def _strip_leading_tokens(words: list[str], skip: set[str]) -> list[str]:
    while words:
        token = words[0].rstrip(".")
        if token in skip:
            words.pop(0)
            continue
        break
    return words


def _is_prep_alternative_phrase(text: str) -> bool:
    return bool(_PREP_ALTERNATIVE_RE.match(text.strip()))


def _strip_prep_words(words: list[str]) -> list[str]:
    while words:
        token = words[0].rstrip(".,")
        if token == "and" and len(words) > 1 and words[1].rstrip(".,") in _PREP_WORDS:
            words.pop(0)
            continue
        if token in _PREP_WORDS:
            words.pop(0)
            continue
        break
    return words


def _is_prep_only_segment(segment: str) -> bool:
    segment = _TRAILING_CLAUSE_RE.sub("", segment).strip()
    if not segment:
        return True
    if segment in _JUNK_ONLY_PHRASES or segment == "more":
        return True
    if _INSTRUCTION_ONLY_RE.match(segment):
        return True
    if _DIMENSION_PREP_SEGMENT_RE.match(segment):
        return True
    if _REMOVED_PREP_SEGMENT_RE.match(segment):
        return True
    if _is_prep_alternative_phrase(segment):
        return True

    segment = _strip_leading_amount(segment)
    words = segment.split()
    if words in (["clove"], ["cloves"]):
        return False
    words = _strip_leading_tokens(words, _UNITS | _SIZES)
    words = _strip_prep_words(words)
    return not words


def _is_junk_only(text: str) -> bool:
    cleaned = text.strip().lower()
    if not cleaned:
        return True

    without_parens = strip_parenthetical_groups(cleaned)
    if _INSTRUCTION_ONLY_RE.match(without_parens):
        return True

    segments = [segment.strip() for segment in without_parens.split(",") if segment.strip()]
    if not segments:
        return True

    return all(_is_prep_only_segment(segment) for segment in segments)


def _prepare_line_for_parsing(line: str) -> str:
    from src.grocery_wizard.ingredients.parsed import (
        _normalize_unicode,
        _strip_leading_to_prefix,
        _strip_optional_prefix,
        _strip_or_prefix,
    )

    return _strip_leading_to_prefix(
        _strip_or_prefix(_strip_optional_prefix(_normalize_unicode(line.strip()).lstrip("-–—− \t")))  # noqa: RUF001
    )
