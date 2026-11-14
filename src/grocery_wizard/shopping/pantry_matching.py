"""Pantry name matching for grocery lists, search, and Notion pantry rows."""

from __future__ import annotations

__all__ = [
    "_matches_pantry_search",
    "generic_pepper_blocks_match",
    "is_pantry_item",
]

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

# ``chili powder`` / ``chile powder`` / ``chilli powder`` are the same pantry staple.
_CHILI_POWDER_HEADS = frozenset({"chili", "chile", "chilli"})


def _is_chili_powder_staple(phrase: str) -> bool:
    words = phrase.split()
    return len(words) == 2 and words[0] in _CHILI_POWDER_HEADS and words[1] == "powder"


def _ingredient_matches_chili_powder_staple(ingredient_name: str, pantry_item_norm: str) -> bool:
    """Match ``ancho chili powder`` and ``kashmiri red chile powder`` to pantry ``chili powder``."""
    if not _is_chili_powder_staple(pantry_item_norm):
        return False
    words = ingredient_name.split()
    return len(words) >= 2 and words[-1] == "powder" and words[-2] in _CHILI_POWDER_HEADS


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


_CHILE_SPELLINGS = frozenset({"chile", "chili", "chilli"})


def _pantry_match_words(text: str) -> list[str]:
    """Lowercase pantry/ingredient words with shared chile/chili spellings unified."""
    words = _pantry_match_key(text).split()
    return ["chili" if word in _CHILE_SPELLINGS else word for word in words]


def _pantry_staple_phrases_match(ingredient_name: str, pantry_item_norm: str) -> bool:
    """True when a multi-word pantry staple matches this ingredient (incl. chile/chili powder)."""
    ingredient_words = _pantry_match_words(ingredient_name)
    pantry_words = _pantry_match_words(pantry_item_norm)
    if not pantry_words or len(pantry_words) == 1:
        return False
    if ingredient_words == pantry_words:
        return True
    return _contains_word_phrase(ingredient_words, pantry_words)


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
        if _pantry_staple_phrases_match(name, item_norm):
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
