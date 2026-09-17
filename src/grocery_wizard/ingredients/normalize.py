"""Grocery-list pipeline: normalize Notion ingredient lines for shopping.

Turns stored (or raw) lines into canonical item names, amounts, and merged
quantities. Notion write paths use ``parsed.py`` + ``sync.py`` instead — see
``ARCHITECTURE.md``.
"""

from __future__ import annotations

__all__ = [
    "clean_ingredient_line_for_storage",
    "count_grocery_nouns",
    "drop_junk_ingredient_lines",
    "expand_ingredient_line",
    "filter_ingredient_key",
    "filter_ingredient_keys",
    "is_instruction_line",
    "is_junk_ingredient",
    "is_metadata_line",
    "is_recipe_step_line",
    "looks_like_merged_ingredient_line",
    "normalize_ingredient",
    "parse_amount",
    "split_compound_ingredients",
    "split_merged_ingredient_line",
    "split_recipe_title_bleed",
]

import re

from src.grocery_wizard.ingredients._cleaning import (
    _is_junk_only,
    _looks_like_ingredient,
    _normalize_unicode_dashes,
    _normalize_unicode_fractions,
    _prepare_line_for_parsing,
    _split_compound_parts_recursive,
    _split_leading_capitalized_ingredient,
)
from src.grocery_wizard.ingredients._patterns import (
    _CHECKLIST_ITEM_RE,
    _CONJUNCTION_SPLIT_RE,
    _GROCERY_NOUNS,
    _INGREDIENT_ALTERNATIVE_RE,
    _INSTRUCTION_ONLY_RE,
    _INSTRUCTION_VERB_RE,
    _LEADING_QTY_RE,
    _MERGED_CAMEL_SPLIT_RE,
    _MERGED_QTY_SPLIT_RE,
    _METADATA_LINE_RE,
    _RECIPE_STEP_RE,
    _TORTILLA_PREFIXES,
    _UNITS,
)
from src.grocery_wizard.ingredients.parsed import (  # noqa: F401
    _format_qty,
    aggregate_amounts,
    format_ingredient_for_storage,
    garlic_clove_count_from_line,
    is_nyt_cooking_url,
    looks_like_stored_ingredient_line,
    minimal_clean_for_storage,
    should_show_amount,
)
from src.grocery_wizard.ingredients.parsed import (
    parse_stored_ingredient as _parse_stored_ingredient,
)

_OIL_PREFIXES = frozenset(
    {
        "canola",
        "coconut",
        "extra-virgin",
        "neutral",
        "olive",
        "sesame",
        "toasted",
        "vegetable",
    }
)

_VINEGAR_PREFIXES = frozenset(
    {
        "apple",
        "balsamic",
        "cider",
        "red",
        "rice",
        "sherry",
        "white",
        "wine",
    }
)

_STOCK_PREFIXES = frozenset(
    {
        "beef",
        "bone",
        "chicken",
        "low-sodium",
        "vegetable",
    }
)

_CREAM_PREFIXES = frozenset({"heavy", "sour", "whipped", "whole-milk"})

# Modifiers before ``beans`` / ``bean`` — keep the phrase intact when both words are
# grocery nouns (e.g. ``butter beans``) or for title-bleed split detection.
_BEANS_PREFIXES = frozenset(
    {
        "black",
        "butter",
        "cannellini",
        "fava",
        "garbanzo",
        "great",
        "kidney",
        "lima",
        "navy",
        "northern",
        "pinto",
        "refried",
        "white",
    }
)

_COUNT_UNITS = frozenset(
    {
        "bag",
        "bags",
        "box",
        "boxes",
        "bunch",
        "bunches",
        "can",
        "cans",
        "clove",
        "cloves",
        "head",
        "heads",
        "jar",
        "jars",
        "leaf",
        "leaves",
        "package",
        "packages",
        "piece",
        "pieces",
        "pkg",
        "slice",
        "slices",
        "sprig",
        "sprigs",
        "stalk",
        "stalks",
        "stick",
        "sticks",
    }
)

_MERGED_LINE_FILLER = frozenset(
    {
        "and",
        "chopped",
        "coarsely",
        "finely",
        "for",
        "fresh",
        "packed",
        "sauce",
        "with",
        "w",
    }
)

_TRAILING_APPENDED_INGREDIENT_RE = re.compile(
    r"(.+?\b(?:to taste|as needed|optional|for garnish|for serving|for topping))\s+"
    r"(?=\S)",
    re.IGNORECASE,
)


def expand_ingredient_line(line: str) -> list[str]:
    """Split compound ingredient lines into separate grocery items."""
    text = _normalize_unicode_fractions(_normalize_unicode_dashes(line.strip()))
    if not text:
        return []

    title_bleed = split_recipe_title_bleed(text)
    if len(title_bleed) > 1:
        expanded: list[str] = []
        for part in title_bleed:
            expanded.extend(_split_compound_parts_recursive(part))
        return expanded

    return _split_compound_parts_recursive(text)


def _split_trailing_appended_ingredient(text: str) -> list[str]:
    """Split a second ingredient accidentally appended after a trailing clause."""
    match = _TRAILING_APPENDED_INGREDIENT_RE.match(text)
    if match is None:
        return [text]
    left = match.group(1).strip()
    right = text[match.end() :].strip()
    if not left or not right or not _looks_like_ingredient(right):
        return [text]
    return [left, right]


def _strip_leading_amount_prefix(text: str) -> tuple[str, str]:
    """Return ``(qty_prefix, rest)`` for a stored ingredient line."""
    rest = text.strip()
    qty_prefix = ""
    qty_match = _LEADING_QTY_RE.match(rest)
    if qty_match:
        qty_prefix = qty_match.group(1).strip()
        rest = rest[qty_match.end() :].strip()
    unit_match = re.match(r"^([A-Za-z]+)\s+", rest)
    if unit_match and unit_match.group(1).lower() in _UNITS:
        qty_prefix = f"{qty_prefix} {unit_match.group(1)}".strip()
        rest = rest[unit_match.end() :].strip()
    return qty_prefix, rest


def _find_grocery_noun_positions(words: list[str]) -> list[int]:
    positions: list[int] = []
    for index, word in enumerate(words):
        if word == "oil" and index > 0 and words[index - 1] in _OIL_PREFIXES:
            if positions and positions[-1] == index - 1:
                positions.pop()
            positions.append(index)
            continue
        if word == "vinegar" and index > 0 and words[index - 1] in _VINEGAR_PREFIXES:
            if positions and positions[-1] == index - 1:
                positions.pop()
            positions.append(index)
            continue
        if word in {"stock", "broth"} and index > 0 and words[index - 1] in _STOCK_PREFIXES:
            if positions and positions[-1] == index - 1:
                positions.pop()
            positions.append(index)
            continue
        if (
            word in {"tortilla", "tortillas"}
            and index > 0
            and words[index - 1] in _TORTILLA_PREFIXES
        ):
            if positions and positions[-1] == index - 1:
                positions.pop()
            positions.append(index)
            continue
        if word == "cream" and index > 0 and words[index - 1] in _CREAM_PREFIXES:
            if positions and positions[-1] == index - 1:
                positions.pop()
            positions.append(index)
            continue
        if word in {"bean", "beans"} and index > 0:
            prev = words[index - 1]
            if prev in _BEANS_PREFIXES or (
                prev == "northern" and index > 1 and words[index - 2] == "great"
            ):
                if positions and positions[-1] == index - 1:
                    positions.pop()
                if (
                    prev == "northern"
                    and index > 1
                    and words[index - 2] == "great"
                    and positions
                    and positions[-1] == index - 2
                ):
                    positions.pop()
                positions.append(index)
                continue
        if word == "cloves" and index + 1 < len(words) and words[index + 1] == "garlic":
            continue
        if word in _GROCERY_NOUNS:
            positions.append(index)
    return positions


def _starts_with_measure_unit(words: list[str]) -> bool:
    if not words:
        return False
    measure_units = _UNITS - _COUNT_UNITS
    return words[0] in measure_units


def _split_words_at_noun_positions(words: list[str], noun_positions: list[int]) -> list[str]:
    parts: list[str] = []
    start = 0
    for position in noun_positions:
        chunk_words = words[start : position + 1]
        while chunk_words and chunk_words[0] in _MERGED_LINE_FILLER:
            chunk_words.pop(0)
        if chunk_words:
            parts.append(" ".join(chunk_words))
        start = position + 1

    if start < len(words):
        trailing = [word for word in words[start:] if word not in _MERGED_LINE_FILLER]
        if trailing:
            parts.append(" ".join(trailing))
    return parts


def _restore_split_casing(original: str, rest: str, parts: list[str]) -> list[str]:
    """Map lowercase split parts back to the casing used in *original*."""
    if not parts:
        return parts
    rest_lower = rest.lower()
    restored: list[str] = []
    cursor = 0
    for part in parts:
        needle = part.lower()
        found = rest_lower.find(needle, cursor)
        if found == -1:
            restored.append(part)
            continue
        restored.append(rest[found : found + len(needle)])
        cursor = found + len(needle)
    return restored


def count_grocery_nouns(text: str) -> int:
    """Count distinct grocery noun anchors on a line (for merge detection)."""
    _, rest = _strip_leading_amount_prefix(text.strip())
    words = rest.lower().split()
    return len(_find_grocery_noun_positions(words))


def _compound_filter_key_start(words: list[str], pos: int) -> int:
    """Index where a compound grocery phrase begins (meal-plan filter keys only)."""
    word = words[pos]
    if word == "oil" and pos > 0:
        start = pos
        while start > 0 and words[start - 1] not in _GROCERY_NOUNS:
            if words[start - 1] in {"or", "and"}:
                break
            start -= 1
        return start
    if word == "vinegar" and pos > 0 and words[pos - 1] in _VINEGAR_PREFIXES:
        start = pos - 1
        if start > 0 and words[start - 1] == "wine":
            start -= 1
        return start
    if (
        word == "cream"
        and pos > 0
        and (words[pos - 1] in _CREAM_PREFIXES or words[pos - 1] == "ice")
    ):
        return pos - 1
    if word in {"tortilla", "tortillas"} and pos > 0 and words[pos - 1] in _TORTILLA_PREFIXES:
        return pos - 1
    if word in {"bean", "beans"} and pos > 0:
        prev = words[pos - 1]
        if prev in _BEANS_PREFIXES:
            return pos - 1
        if prev == "northern" and pos > 1 and words[pos - 2] == "great":
            return pos - 2
    return pos


def _sanitize_filter_words(text: str) -> list[str]:
    """Tokenize for meal-plan filter keys; strip punctuation stuck to tokens."""
    cleaned = re.sub(r"[,;]", " ", text)
    words: list[str] = []
    for raw in cleaned.lower().split():
        word = raw.strip(".,;:!()[]")
        if word:
            words.append(word)
    return words


def _strip_filter_line_prefix(line: str) -> str:
    stripped = line.strip()
    for prefix in ("[x]", "▢", "•", "*"):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return stripped


def _segment_has_filter_noun(segment: str) -> bool:
    prepared = _strip_filter_line_prefix(segment)
    source = normalize_ingredient(prepared) or prepared
    return bool(_find_grocery_noun_positions(_sanitize_filter_words(source)))


def _segment_contributes_filter_key(part: str) -> bool:
    lowered = part.lower().strip()
    if lowered.startswith("for "):
        return False
    if is_junk_ingredient(part):
        return False
    if _segment_has_filter_noun(part):
        return True
    prepared = _strip_filter_line_prefix(part)
    normalized = normalize_ingredient(prepared)
    if not normalized:
        return False
    return len(_sanitize_filter_words(normalized)) <= 3


def _filter_line_segments(line: str) -> list[str]:
    """Split stored lines into parts that each contribute filter keys."""
    from src.grocery_wizard.ingredients.parsed import _normalize_unicode

    text = _strip_filter_line_prefix(line)
    text = _normalize_unicode(_normalize_unicode_dashes(text))
    if not text:
        return []
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) <= 1:
        return [text]
    contributors = [part for part in parts if _segment_contributes_filter_key(part)]
    if len(contributors) >= 2:
        return contributors
    if contributors:
        return [contributors[0]]
    return [text]


def _filter_key_from_words(words: list[str]) -> str:
    from src.grocery_wizard.ingredients.parsed import _prefer_plural_form

    if not words:
        return ""
    positions = _find_grocery_noun_positions(words)
    if not positions:
        return _prefer_plural_form(" ".join(words))
    pos = positions[-1]
    start = _compound_filter_key_start(words, pos)
    chunk = " ".join(words[start : pos + 1])
    return _prefer_plural_form(chunk)


def _filter_key_from_segment(segment: str) -> str:
    """Coarse staple key for one ingredient segment (meal-plan filters only)."""
    prepared = _strip_filter_line_prefix(segment)
    source = normalize_ingredient(prepared) or prepared
    if source.startswith(("[x]", "▢", "•", "*")):
        stripped = _strip_filter_line_prefix(source)
        source = normalize_ingredient(stripped) or stripped
    return _filter_key_from_words(_sanitize_filter_words(source))


def filter_ingredient_keys(line: str) -> set[str]:
    """Return canonical staple keys for meal-plan ingredient filters."""
    if is_junk_ingredient(line):
        return set()
    keys: set[str] = set()
    for segment in _filter_line_segments(line):
        key = _filter_key_from_segment(segment)
        if key:
            keys.add(key)
    return keys


def filter_ingredient_key(line: str) -> str:
    """Return one canonical staple key (first sorted) for meal-plan filters."""
    keys = filter_ingredient_keys(line)
    if not keys:
        return ""
    return min(keys)


def looks_like_merged_ingredient_line(text: str) -> bool:
    """Return True when a stored line likely contains multiple ingredients."""
    stripped = text.strip()
    if not stripped or is_junk_ingredient(stripped):
        return False
    if _CONJUNCTION_SPLIT_RE.search(stripped):
        return False
    if looks_like_stored_ingredient_line(stripped) and "," in stripped:
        appended = _split_trailing_appended_ingredient(stripped)
        if len(appended) > 1:
            return True
    return count_grocery_nouns(stripped) >= 2


def split_recipe_title_bleed(text: str) -> list[str]:
    """Split concatenated recipe-title artifacts into separate grocery items."""
    stripped = text.strip()
    if not stripped:
        return [text]

    appended = _split_trailing_appended_ingredient(stripped)
    if len(appended) > 1:
        expanded: list[str] = []
        for part in appended:
            expanded.extend(split_recipe_title_bleed(part))
        return expanded

    # Real compound ingredients use conjunctions; title bleed does not.
    if _CONJUNCTION_SPLIT_RE.search(stripped):
        return [text]

    if _INGREDIENT_ALTERNATIVE_RE.search(stripped):
        return [text]

    if "(" in stripped and ")" in stripped:
        return [text]

    if re.match(
        r"^(?:chopped|fresh|sliced|diced|minced|grated|peeled|beaten|smashed|packed)\b",
        stripped,
        re.IGNORECASE,
    ):
        return [text]

    # ``gnocchi sauce veggie for gnocchi`` → ``gnocchi``, ``veggie for gnocchi``
    repeat_match = re.match(
        r"^(\w+)\s+(?:\w+\s+)*(\w+)\s+for\s+\1\s*$",
        stripped,
        re.IGNORECASE,
    )
    if repeat_match:
        noun = repeat_match.group(1)
        middle = repeat_match.group(2)
        return [noun, f"{middle} for {noun}"]

    qty_prefix, rest = _strip_leading_amount_prefix(stripped)
    words = rest.lower().split()
    if len(words) < 2:
        return [text]

    if _starts_with_measure_unit(words):
        return [text]

    noun_positions = _find_grocery_noun_positions(words)
    if len(noun_positions) < 2:
        return [text]

    parts = _split_words_at_noun_positions(words, noun_positions)
    if len(parts) < 2:
        return [text]

    parts = _restore_split_casing(stripped, rest, parts)
    if qty_prefix:
        parts[0] = f"{qty_prefix} {parts[0]}".strip()
    return parts


def split_compound_ingredients(text: str) -> list[str]:
    """Expand compound ingredient lines in multiline text to one item per line."""
    if not text or not text.strip():
        return []

    expanded: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        expanded.extend(expand_ingredient_line(line))
    return expanded


def is_junk_ingredient(line: str) -> bool:
    """Return True when a line is only prep instructions, not a grocery item."""
    from src.grocery_wizard.ingredients.parsed import _strip_optional_prefix

    return _is_junk_only(_strip_optional_prefix(line.strip()))


def drop_junk_ingredient_lines(lines: list[str]) -> list[str]:
    """Remove prep-only instruction lines from scraped ingredient lists."""
    return [line for line in lines if line.strip() and not is_junk_ingredient(line)]


def is_metadata_line(line: str) -> bool:
    """Return True for yield/serves headers, not grocery items."""
    return bool(_METADATA_LINE_RE.match(line.strip()))


def is_instruction_line(line: str) -> bool:
    """Return True when a line is a cooking step, not a grocery item."""
    stripped = line.strip()
    if not stripped:
        return True
    if _RECIPE_STEP_RE.match(stripped):
        return True
    if is_metadata_line(stripped):
        return True
    if _INSTRUCTION_VERB_RE.match(stripped):
        return True
    if _INSTRUCTION_ONLY_RE.match(stripped):
        return True
    return len(stripped) > 100 and bool(_INSTRUCTION_VERB_RE.search(stripped))


def is_recipe_step_line(line: str) -> bool:
    """Return True for numbered recipe steps (truncate remaining lines after)."""
    stripped = line.strip()
    if _CHECKLIST_ITEM_RE.match(stripped):
        return False
    return bool(_RECIPE_STEP_RE.match(stripped))


def split_merged_ingredient_line(line: str) -> list[str]:
    """Split scrape artifacts where multiple ingredients were joined on one line."""
    text = _normalize_unicode_dashes(line.strip())
    if not text:
        return []

    parts: list[str] = []
    for raw_segment in _MERGED_CAMEL_SPLIT_RE.split(text):
        segment = raw_segment.strip()
        if not segment:
            continue
        for raw_piece in _MERGED_QTY_SPLIT_RE.split(segment):
            piece = raw_piece.strip()
            if not piece:
                continue
            parts.extend(_split_leading_capitalized_ingredient(piece))
    return parts or [text]


def clean_ingredient_line_for_storage(line: str) -> str:
    return format_ingredient_for_storage(line)


def normalize_ingredient(line: str) -> str:
    """Return the canonical grocery item name from a stored or raw ingredient line."""
    from src.grocery_wizard.ingredients.parsed import (
        _needs_display_prep_strip,
        _normalize_unicode,
        _parse_with_library,
        _prefer_plural_form,
        _should_preserve_raw_line,
        _simplify_parsed_name,
        _strip_parenthetical_notes,
        _strip_size_descriptors,
        _strip_trailing_prep_commas,
    )

    if is_junk_ingredient(line):
        return ""
    if re.search(r"<br\s*/?>", line, re.IGNORECASE):
        parts = re.split(r"<br\s*/?>", line, flags=re.IGNORECASE)
        return "<br/>".join(normalize_ingredient(part) for part in parts if part.strip())

    stripped = line.strip()
    if stripped.startswith("[x]"):
        text = _strip_trailing_prep_commas(_normalize_unicode(stripped))
        text = re.sub(r",\s*optional\s*$", "", text, flags=re.IGNORECASE).strip()
        return text.lower()
    if stripped.startswith(("▢", "•", "*")):
        bullet = stripped[0]
        content = stripped[1:].strip()
        formatted = format_ingredient_for_storage(content) or _strip_trailing_prep_commas(content)
        return f"{bullet} {formatted}".lower()

    if _should_preserve_raw_line(line):
        parse_text = _strip_parenthetical_notes(_prepare_line_for_parsing(line))
        if not parse_text:
            return ""
        parsed = _parse_with_library(parse_text)
        name = _simplify_parsed_name(parsed.name[0].text) if parsed.name else parse_text
        name = _prefer_plural_form(_strip_size_descriptors(name))
        if re.search(r"\b1\b", line) and " cube" in line.lower() and name.endswith("cubes"):
            name = name[:-1]
        return name.lower()

    prepared = _prepare_line_for_parsing(line)
    if (
        prepared
        and looks_like_stored_ingredient_line(prepared)
        and not _needs_display_prep_strip(prepared)
    ):
        name, _ = _parse_stored_ingredient(prepared)
        return name.lower()

    stored = format_ingredient_for_storage(line)
    if not stored:
        return ""
    name, _ = _parse_stored_ingredient(stored)
    return name.lower()


def parse_amount(line: str) -> tuple[str, str | None]:
    """Parse an ingredient line into ``(name, amount | None)``."""
    from src.grocery_wizard.ingredients.parsed import _needs_display_prep_strip

    if is_junk_ingredient(line):
        return "", None
    text = _prepare_line_for_parsing(line)
    if not text:
        return "", None
    if not looks_like_stored_ingredient_line(text) or _needs_display_prep_strip(text):
        stored = format_ingredient_for_storage(line)
        if not stored:
            return "", None
        name, amount = _parse_stored_ingredient(stored)
        if name == "garlic" and amount is None:
            clove_count = garlic_clove_count_from_line(line)
            if clove_count is not None:
                return name, f"clove:{_format_qty(clove_count)}"
        return name, amount
    return _parse_stored_ingredient(text)
