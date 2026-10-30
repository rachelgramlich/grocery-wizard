"""Pantry staples — items assumed on hand and excluded from grocery lists."""

from __future__ import annotations

__all__ = [
    "PantrySection",
    "append_pantry_item",
    "format_pantry_display",
    "is_pantry_item",
    "load_pantry",
    "parse_pantry_file",
    "remove_pantry_item_by_name",
    "write_pantry_file",
]

from dataclasses import dataclass, field
from pathlib import Path


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
    from src.grocery_wizard.integrations.notion_household import NotionPantryDB

    return NotionPantryDB().load_item_names()


# Only these phrases are table pepper. A pantry/removal entry with one of them may match
# ``pepper``, ``black pepper`` and ``ground black pepper`` and nothing else (not ``fresno pepper``,
# ``red bell pepper``, ``jalapeno pepper``, ``pepper jack``, ...).
_GENERIC_PEPPER_PANTRY = frozenset({"pepper", "peppers", "black pepper", "ground black pepper"})
_PEPPER_CONNECTORS = frozenset({"and", "&"})


def _pepper_word_is_table_pepper(words: list[str], index: int) -> bool:
    """True when the ``pepper`` word at *index* is plain, black, or ground black pepper."""
    if index + 1 < len(words) and words[index + 1] not in _PEPPER_CONNECTORS:
        return False
    if index == 0 or words[index - 1] in _PEPPER_CONNECTORS:
        return True
    if words[index - 1] != "black":
        return False
    return index == 1 or words[index - 2] in _PEPPER_CONNECTORS or words[index - 2] == "ground"


def generic_pepper_blocks_match(ingredient_name: str, pepper_phrase: str) -> bool:
    """True when generic pantry/removal ``pepper`` must not match this ingredient.

    Only ``pepper``, ``black pepper`` and ``ground black pepper`` are table pepper.
    Any other pepper (``fresno pepper``, ``green pepper``, ``red pepper``) is produce or a
    different product and stays on the list.
    """
    if _pantry_match_key(pepper_phrase) not in _GENERIC_PEPPER_PANTRY:
        return False
    words = _pantry_match_key(ingredient_name).split()
    for index, word in enumerate(words):
        if word == "peppers":
            return True
        if word == "pepper" and not _pepper_word_is_table_pepper(words, index):
            return True
    return False


# Generic ``beans`` is not the same as named varieties (``butter beans``, ``white beans``).
_GENERIC_BEANS_PANTRY = frozenset({"bean", "beans"})

# Pantry ``rice`` is not cauliflower-based stand-ins (``cauliflower rice``).
_GENERIC_RICE_PANTRY = frozenset({"rice"})
_NOT_ACTUAL_RICE_PHRASES = frozenset({"cauliflower rice", "riced cauliflower"})

# Pantry ``frozen …`` / ``canned …`` are specific products — not plain last-word staples.
_PANTRY_SPECIFIC_PRODUCT_PREFIXES = frozenset({"canned", "frozen"})

# Spreads named ``… butter`` are not dairy butter on the pantry list.
_NOT_DAIRY_BUTTER_PHRASES = frozenset(
    {
        "peanut butter",
        "almond butter",
        "apple butter",
        "cashew butter",
        "sunflower butter",
        "cookie butter",
        "butter lettuce",
    }
)


def _pantry_match_key(text: str) -> str:
    return text.strip().lower().replace("-", " ")


def _is_named_bean_ingredient(ingredient_name: str) -> bool:
    """True for grocery items like ``black beans`` (not a single word ``beans``)."""
    words = ingredient_name.split()
    return len(words) >= 2 and words[-1] in ("bean", "beans")


def _pantry_last_word_match(ingredient_name: str, pantry_item_norm: str) -> bool:
    """True when a single-word ingredient matches the last word of a pantry phrase."""
    name_words = ingredient_name.split()
    item_words = pantry_item_norm.split()
    if len(name_words) != 1 or len(item_words) <= 1 or item_words[-1] != name_words[0]:
        return False
    prefix = item_words[0]
    return not (prefix in _PANTRY_SPECIFIC_PRODUCT_PREFIXES and prefix not in name_words)


def _skip_pantry_phrase_match(ingredient_name: str, pantry_item_norm: str) -> bool:
    """Return True when a pantry staple must not match this ingredient name."""
    if pantry_item_norm == "butter" and ingredient_name in _NOT_DAIRY_BUTTER_PHRASES:
        return True
    if pantry_item_norm in _GENERIC_RICE_PANTRY and ingredient_name in _NOT_ACTUAL_RICE_PHRASES:
        return True
    if not _is_named_bean_ingredient(ingredient_name):
        return False
    if pantry_item_norm in _GENERIC_BEANS_PANTRY:
        return True
    # ``black`` in the pantry is not ``black beans``; same for ``butter``, ``kidney``, etc.
    pantry_words = pantry_item_norm.split()
    return len(pantry_words) == 1 and pantry_item_norm in ingredient_name.split()[:-1]


def is_pantry_item(normalized: str, pantry: set[str]) -> bool:
    """Return True if normalized ingredient matches a pantry item.

    Pantry items match when they appear as a consecutive word phrase in the
    ingredient (e.g. pantry ``salt`` matches ``kosher salt``). We do not match
    the reverse (ingredient word appearing inside a longer pantry phrase like
    ``beef stock``).
    """
    name = _pantry_match_key(normalized)
    if not name:
        return False

    name_words = name.split()

    for item in pantry:
        item_norm = _pantry_match_key(item)
        if generic_pepper_blocks_match(name, item_norm):
            continue
        if _skip_pantry_phrase_match(name, item_norm):
            continue
        if name == item_norm:
            return True
        if _contains_word_phrase(name_words, item_norm.split()):
            return True
        # Narrow reverse rule: single-token ingredient (e.g. "oil") matches
        # when it equals the *last* word of a multi-word pantry phrase
        # (e.g. "olive oil", "vegetable oil").  This avoids re-introducing
        # broad false positives like "beef" matching "beef stock".
        if _pantry_last_word_match(name, item_norm):
            return True
    return False


def _contains_word_phrase(haystack_words: list[str], needle_words: list[str]) -> bool:
    if not needle_words or len(needle_words) > len(haystack_words):
        return False
    width = len(needle_words)
    for index in range(len(haystack_words) - width + 1):
        if haystack_words[index : index + width] == needle_words:
            return True
    return False


def _matches_pantry_search(search: str, item: str) -> bool:
    """Return True if search term identifies a pantry item by name."""
    lowered_search = search.strip().lower()
    lowered_item = item.strip().lower()
    if not lowered_search or not lowered_item:
        return False
    if lowered_search == lowered_item:
        return True
    if generic_pepper_blocks_match(lowered_item, lowered_search) or generic_pepper_blocks_match(
        lowered_search, lowered_item
    ):
        return False
    if lowered_item.startswith(lowered_search):
        return True

    search_words = lowered_search.split()
    item_words = lowered_item.split()
    return _contains_word_phrase(search_words, item_words) or _contains_word_phrase(
        item_words, search_words
    )


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
        lines = [
            "# Pantry staples — one item per line.",
            "# Lines starting with # are section headers or comments.",
            "",
            "# --- Uncategorized ---",
        ]

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
        from src.grocery_wizard.integrations.notion_household import NotionPantryDB

        return NotionPantryDB().append_item(name, section=section)

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
        from src.grocery_wizard.integrations.notion_household import NotionPantryDB

        return NotionPantryDB().remove_item_by_name(search)

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
