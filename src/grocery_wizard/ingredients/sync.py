"""Notion ingredient storage pipeline: clean, format, parse, and merge lines.

Orchestrates the **storage pipeline** (``parsed.py`` + line filters from
``normalize.py``). See ``ARCHITECTURE.md``.
"""

from __future__ import annotations

import re

from src.grocery_wizard.ingredients.normalize import (
    expand_ingredient_line,
    is_instruction_line,
    is_junk_ingredient,
    is_metadata_line,
    is_recipe_step_line,
    looks_like_merged_ingredient_line,
    split_merged_ingredient_line,
)
from src.grocery_wizard.ingredients.parsed import (
    format_ingredient_for_storage,
    format_stored_line_for_display,
    is_nyt_cooking_url,
    minimal_clean_for_storage,
    name_from_stored_line,
)
from src.grocery_wizard.recipes.scraper import ingredients_to_text
from src.grocery_wizard.shopping.line_items import strip_line_item
from src.grocery_wizard.shopping.pantry import fresh_colored_pepper_blocks_generic_pepper

_REMOVAL_PREFIX_RE = re.compile(r"^remove\s*:?\s*(.+)$", re.IGNORECASE)
_REMOVAL_DASH_RE = re.compile(r"^-\s+(.+)$")
_BR_SPLIT = re.compile(r"<br\s*/?>", re.IGNORECASE)


def split_ingredients_text(text: str) -> str:
    """Re-split stored ingredients, preserving directives and comments."""
    if not text or not text.strip():
        return ""

    output_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if is_directive(line):
            output_lines.append(line)
            continue
        output_lines.extend(expand_ingredient_line(line))
    return ingredients_to_text(output_lines)


def _normalize_stored_lines(text: str) -> list[str]:
    """Normalize bullets, HTML breaks, and unicode from stored ingredient text."""
    if not text or not text.strip():
        return []

    normalized = _BR_SPLIT.sub("\n", text)
    lines: list[str] = []
    for raw_line in normalized.splitlines():
        stripped_raw = raw_line.strip()
        if stripped_raw and is_removal_directive(stripped_raw):
            lines.append(stripped_raw)
            continue
        line = strip_line_item(raw_line)
        if not line:
            continue
        line = re.sub(r"^[▢•*]\s*", "", line)
        line = re.sub(r"^\\[ \\]\s*▢?", "", line).strip()
        line = re.sub(r"^\d+\.\s*(?:\[\s*\]\s*)", "", line).strip()
        if line.startswith(("- ", "* ")) and not is_removal_directive(line):
            line = line[2:].strip()
        elif len(line) > 1 and line[0] == "-" and line[1].isdigit():
            line = line[1:].strip()
        if line:
            lines.append(line)
    return lines


def _repair_mangled_lines(lines: list[str]) -> list[str]:
    """Split merged scrape artifacts into one ingredient per line."""
    repaired: list[str] = []
    for line in lines:
        if is_directive(line):
            repaired.append(line)
            continue
        repaired.extend(split_merged_ingredient_line(line))
    return repaired


def _merge_continuation_lines(lines: list[str]) -> list[str]:
    """Join ingredient lines broken across rows (e.g. unclosed parentheses)."""
    merged: list[str] = []
    for line in lines:
        if is_directive(line):
            merged.append(line)
            continue
        stripped = line.strip()
        if (
            is_junk_ingredient(stripped)
            or is_instruction_line(stripped)
            or is_metadata_line(stripped)
        ):
            merged.append(stripped)
            continue
        if (
            merged
            and not is_directive(merged[-1])
            and _is_ingredient_continuation(merged[-1], stripped)
        ):
            merged[-1] = f"{merged[-1]} {stripped}"
        else:
            merged.append(stripped)
    return merged


def _is_ingredient_continuation(previous: str, current: str) -> bool:
    if looks_like_merged_ingredient_line(previous):
        return False
    stripped = current.strip()
    if not stripped:
        return False
    if re.match(r"^and\b", stripped, re.IGNORECASE):
        return True
    if previous.count("(") > previous.count(")"):
        return True
    if previous.rstrip().endswith(","):
        return True
    return (
        "," in previous
        and stripped[0].islower()
        and not re.match(r"^\d", stripped)
        and not looks_like_merged_ingredient_line(stripped)
    )


def _stored_ingredient_lines(text: str) -> list[str]:
    """Normalize Notion ingredient text and join wrapped continuation rows."""
    return _merge_continuation_lines(_normalize_stored_lines(text))


def _truncate_at_instructions(lines: list[str]) -> list[str]:
    """Drop recipe steps and everything after the first numbered instruction."""
    kept: list[str] = []
    for line in lines:
        if is_directive(line):
            kept.append(line)
            continue
        if is_recipe_step_line(line):
            break
        if is_metadata_line(line) or is_instruction_line(line):
            continue
        kept.append(line)
    return kept


def prepare_ingredients_for_notion(
    text: str,
    *,
    source_url: str | None = None,
    force_full_format: bool = False,
) -> str:
    """Clean, split, and normalize ingredient text before storing in Notion."""
    lines = _normalize_stored_lines(text)
    if not lines:
        return ""

    lines = _repair_mangled_lines(lines)
    lines = _merge_continuation_lines(lines)
    lines = _truncate_at_instructions(lines)

    split = split_ingredients_text(ingredients_to_text(lines))
    if not split.strip():
        return ""

    use_minimal_cleanup = is_nyt_cooking_url(source_url) and not force_full_format
    kept: list[str] = []
    for line in split.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if is_directive(stripped):
            kept.append(stripped)
            continue
        if (
            is_metadata_line(stripped)
            or is_instruction_line(stripped)
            or is_junk_ingredient(stripped)
        ):
            continue
        if stripped.lower() == "recipe":
            continue
        if use_minimal_cleanup:
            cleaned = minimal_clean_for_storage(stripped)
        else:
            cleaned = format_ingredient_for_storage(stripped)
        if cleaned:
            kept.append(cleaned)
    return ingredients_to_text(kept)


def format_ingredients_for_review(text: str) -> str:
    """Convert Notion storage lines to readable text for the grocery review step."""
    if not text.strip():
        return text
    formatted: list[str] = []
    for line in _stored_ingredient_lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        if is_directive(stripped):
            formatted.append(stripped)
            continue
        formatted.append(format_stored_line_for_display(line))
    return "\n".join(formatted)


def is_removal_directive(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _REMOVAL_PREFIX_RE.match(stripped):
        return True
    match = _REMOVAL_DASH_RE.match(stripped)
    if not match:
        return False
    target = match.group(1).strip()
    if target.startswith("["):
        return False
    return not re.match(r"^\d", target)


def is_directive(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    return is_removal_directive(stripped)


def parse_removal_target(line: str) -> str:
    stripped = line.strip()
    match = _REMOVAL_PREFIX_RE.match(stripped)
    if match:
        return match.group(1).strip()
    match = _REMOVAL_DASH_RE.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def parse_ingredients_text(text: str) -> tuple[list[str], list[str]]:
    """Split stored ingredients into ingredient lines and removal targets."""
    ingredients: list[str] = []
    removals: list[str] = []
    if not text or not text.strip():
        return ingredients, removals

    for line in _stored_ingredient_lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        if is_directive(stripped):
            if is_removal_directive(stripped):
                target = parse_removal_target(stripped)
                if target:
                    removals.append(target)
            continue
        ingredients.append(stripped)

    return ingredients, removals


def _normalized_set(lines: list[str]) -> set[str]:
    return {norm for line in lines if (norm := name_from_stored_line(line))}


def _line_represented(line: str, normalized_names: set[str]) -> bool:
    norm = name_from_stored_line(line)
    if not norm:
        return False
    return norm in normalized_names


def _matches_removal(line: str, removal_target: str) -> bool:
    normalized = name_from_stored_line(line)
    target_norm = name_from_stored_line(removal_target)
    if not normalized or not target_norm:
        return False
    if fresh_colored_pepper_blocks_generic_pepper(normalized, target_norm):
        return False
    if normalized == target_norm:
        return True
    name_words = normalized.split()
    target_words = target_norm.split()
    if _ingredient_contains_word_phrase(name_words, target_words):
        return True
    return _ingredient_contains_word_phrase(target_words, name_words)


def _ingredient_contains_word_phrase(haystack_words: list[str], needle_words: list[str]) -> bool:
    if not needle_words or len(needle_words) > len(haystack_words):
        return False
    width = len(needle_words)
    for index in range(len(haystack_words) - width + 1):
        if haystack_words[index : index + width] == needle_words:
            return True
    return False


def apply_removals(lines: list[str], removal_targets: list[str]) -> list[str]:
    if not removal_targets:
        return list(lines)
    return [
        line
        for line in lines
        if not any(_matches_removal(line, target) for target in removal_targets)
    ]


def merge_ingredients(existing: str, scraped: str) -> str:
    """Merge Notion ingredients with a freshly scraped list."""
    existing_lines, removals = parse_ingredients_text(existing)
    scraped_lines, _ = parse_ingredients_text(scraped)

    merged = list(scraped_lines)
    merged_norms = _normalized_set(scraped_lines)

    for line in existing_lines:
        if _line_represented(line, merged_norms):
            continue
        norm = name_from_stored_line(line)
        if not norm:
            continue
        merged.append(line)
        merged_norms.add(norm)

    merged = apply_removals(merged, removals)
    return ingredients_to_text(merged)
