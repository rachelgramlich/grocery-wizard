"""Pantry staples — items assumed on hand and excluded from grocery lists."""

from __future__ import annotations

__all__ = [
    "DEFAULT_EMPTY_PANTRY_LINES",
    "PantrySection",
    "append_pantry_item",
    "format_pantry_display",
    "generic_pepper_blocks_match",
    "is_pantry_item",
    "load_pantry",
    "parse_pantry_file",
    "remove_pantry_item_by_name",
    "write_pantry_file",
]

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from src.grocery_wizard.integrations.notion.lazy_household import notion_pantry_db
from src.grocery_wizard.shopping.pantry_matching import (
    _matches_pantry_search,
    generic_pepper_blocks_match,
    is_pantry_item,
)

DEFAULT_EMPTY_PANTRY_LINES: Final[tuple[str, ...]] = (
    "# Pantry staples — one item per line.",
    "# Lines starting with # are section headers or comments.",
    "",
    "# --- Uncategorized ---",
)


def _load_pantry_from_file(pantry_path: Path) -> set[str]:
    if not pantry_path.exists():
        return set()

    items: set[str] = set()
    for raw_line in pantry_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lower()
        if line and not line.startswith("#"):
            items.add(line)
    return items


def load_pantry(path: Path | None = None) -> set[str]:
    """Load pantry item names (Notion by default; optional file path for tests)."""
    if path is not None:
        return _load_pantry_from_file(path)
    return notion_pantry_db().load_item_names()


@dataclass
class PantrySection:
    """A section header and its pantry items (line indices into the source file)."""

    header: str | None
    items: list[tuple[int, str]] = field(default_factory=list)


def parse_pantry_file(path: Path) -> tuple[list[str], list[PantrySection]]:
    """Parse pantry.txt into raw lines and display sections."""
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = list(DEFAULT_EMPTY_PANTRY_LINES)

    sections: list[PantrySection] = []
    current = PantrySection(header=None)

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            if current.header is not None or current.items:
                sections.append(current)
            current = PantrySection(header=raw_line)
        elif stripped:
            current.items.append((index, stripped))

    if current.header is not None or current.items:
        sections.append(current)

    if not sections:
        sections = [PantrySection(header="# --- Uncategorized ---")]

    return lines, sections


def write_pantry_file(path: Path, lines: list[str]) -> None:
    """Write pantry lines back to disk, ensuring a trailing newline."""
    text = "\n".join(lines)
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def append_pantry_item(name: str, path: Path | None = None, *, section: str | None = None) -> bool:
    """Append an item to the pantry (last section). Returns False if invalid or duplicate."""
    if path is None:
        return notion_pantry_db().append_item(name, section=section)

    pantry_path = path
    cleaned = name.strip()
    if not cleaned or cleaned.startswith("#"):
        return False

    lines, sections = parse_pantry_file(pantry_path)
    flat = _flatten_items(sections)
    if any(_matches_pantry_search(cleaned, item) for _idx, item in flat):
        return False

    target = sections[-1] if sections else PantrySection(header="# --- Uncategorized ---")
    if not sections:
        sections.append(target)
        lines.append(target.header or "# --- Uncategorized ---")

    insert_at = len(lines)
    if target.items:
        insert_at = target.items[-1][0] + 1
    elif target.header is not None:
        try:
            insert_at = lines.index(target.header) + 1
        except ValueError:
            insert_at = len(lines)

    lines.insert(insert_at, cleaned)
    write_pantry_file(pantry_path, lines)
    return True


def remove_pantry_item_by_name(search: str, path: Path | None = None) -> bool:
    """Remove the first pantry item matching *search*. Returns False if no match."""
    if path is None:
        return notion_pantry_db().remove_item_by_name(search)

    pantry_path = path
    lines, sections = parse_pantry_file(pantry_path)
    flat = _flatten_items(sections)
    if not flat:
        return False

    line_index: int | None = None
    for idx, item in flat:
        if _matches_pantry_search(search, item):
            line_index = idx
            break

    if line_index is None:
        return False

    lines.pop(line_index)
    write_pantry_file(pantry_path, lines)
    return True


def _flatten_items(sections: list[PantrySection]) -> list[tuple[int, str]]:
    return [entry for section in sections for entry in section.items]


def format_pantry_display(sections: list[PantrySection]) -> str:
    """Format pantry sections for terminal display."""
    parts: list[str] = []
    item_number = 1
    for section in sections:
        if section.header:
            parts.append(section.header)
        for _index, item in section.items:
            parts.append(f"  {item_number}. {item}")
            item_number += 1
        if section.items:
            parts.append("")
    return "\n".join(parts).rstrip()


def parse_pantry_file_from_lines(lines: list[str]) -> tuple[list[str], list[PantrySection]]:
    """Re-parse in-memory pantry lines (same rules as parse_pantry_file)."""
    sections: list[PantrySection] = []
    current = PantrySection(header=None)

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            if current.header is not None or current.items:
                sections.append(current)
            current = PantrySection(header=raw_line)
        elif stripped:
            current.items.append((index, stripped))

    if current.header is not None or current.items:
        sections.append(current)

    if not sections:
        sections = [PantrySection(header="# --- Uncategorized ---")]

    return lines, sections
