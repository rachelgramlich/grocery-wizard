"""Store aisle ordering and ingredient classification for grocery lists."""

from __future__ import annotations

__all__ = [
    "StoreAisleConfig",
    "aisle_label",
    "canonical_pantry_section_label",
    "group_grocery_items_by_aisle",
    "ingredient_name",
    "is_legacy_notion_aisle_label",
    "load_store_aisles",
    "pantry_aisle_for_item",
    "pantry_aisle_section_labels",
    "resolve_pantry_aisle_id",
    "sort_grocery_items",
    "strip_checklist_prefix",
]

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from src.grocery_wizard.config import STORE_AISLES_PATH
from src.grocery_wizard.ingredients.normalize import parse_amount
from src.grocery_wizard.shopping.line_items import strip_checklist_prefix

# Notion rows may still use labels from before the dry-goods split.
_LEGACY_NOTION_AISLE_LABELS = frozenset(
    {
        "dry goods / cans / cereal / rice",
        "dry goods",
        "canned drinks",
        "crackers & cookies",
        "snacks",
        "nuts & dried fruit",
        "rice grains & cereal",
        "pasta & noodles",
        "canned goods",
    }
)

_SECTION_HEADER_RE = re.compile(r"^#\s*---\s*(?P<id>.+?)(?::\s*(?P<label>.+?))?\s*---\s*$")
_PRODUCT_LINE_RE = re.compile(r"^(?P<aisle>[^:]+):\s*(?P<phrase>.+)$")
_PRODUCTS_SECTION_ID = "products"

# Trailing prep phrases (after a comma) stripped before keyword matching so
# ``lime, juiced`` and ``potatoes, unpeeled but scrubbed clean`` classify correctly.
_PREP_SUFFIX_RE = re.compile(
    r",\s*(?:"
    r"juiced|zested|"
    r"unpeeled(?:\s+but\s+[^,]+)?|"
    r"beaten|chopped|diced|minced|sliced|grated|shredded|crushed|peeled|seeded|cored|"
    r"trimmed|halved|quartered|julienned|cubed|mashed|softened|melted|thawed|rinsed|drained|"
    r"smashed(?:\s+and\s+peeled)?|peeled\s+and\s+grated|minced\s+or\s+grated|"
    r"(?:light\s+green(?:\s+\w+)*\s+)?(?:white\s+)?parts\s+only"
    r")(?:\s+.*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class StoreAisleConfig:
    aisle_order: tuple[str, ...]
    aisle_labels: dict[str, str]
    aisle_keywords: dict[str, tuple[str, ...]]
    product_phrases: tuple[tuple[str, str], ...] = ()


def parse_store_aisles_file(path: Path) -> StoreAisleConfig:
    """Parse store aisle order, labels, and keywords from a config file."""
    aisle_order: list[str] = []
    aisle_labels: dict[str, str] = {}
    aisle_keywords: dict[str, list[str]] = {}
    product_phrases: list[tuple[str, str]] = []
    current_aisle: str | None = None
    in_products = False

    if not path.exists():
        return StoreAisleConfig((), {}, {})

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        header_match = _SECTION_HEADER_RE.match(stripped)
        if header_match:
            aisle_id = header_match.group("id").strip().lower()
            label = (header_match.group("label") or aisle_id).strip()
            if aisle_id == _PRODUCTS_SECTION_ID:
                in_products = True
                current_aisle = None
                continue
            in_products = False
            aisle_order.append(aisle_id)
            aisle_labels[aisle_id] = label
            aisle_keywords[aisle_id] = []
            current_aisle = aisle_id
            continue

        if stripped.startswith("#"):
            continue

        if in_products:
            product_match = _PRODUCT_LINE_RE.match(stripped)
            if product_match:
                aisle = product_match.group("aisle").strip().lower()
                phrase = product_match.group("phrase").strip().lower()
                product_phrases.append((phrase, aisle))
            continue

        if current_aisle is None:
            continue

        aisle_keywords[current_aisle].append(stripped.lower())

    if "other" not in aisle_order:
        aisle_order.append("other")
        aisle_labels.setdefault("other", "Other")
        aisle_keywords.setdefault("other", [])

    product_phrases.sort(key=lambda pair: len(pair[0].split()), reverse=True)

    return StoreAisleConfig(
        aisle_order=tuple(aisle_order),
        aisle_labels=aisle_labels,
        aisle_keywords={aisle: tuple(words) for aisle, words in aisle_keywords.items()},
        product_phrases=tuple(product_phrases),
    )


_aisle_config_cache: dict[str, tuple[tuple[int, int], StoreAisleConfig]] = {}


def load_store_aisles(path: str | None = None) -> StoreAisleConfig:
    """Load store aisle config from the committed config file."""
    resolved = Path(path) if path else STORE_AISLES_PATH
    cache_key = str(resolved.resolve())
    if resolved.exists():
        stat = resolved.stat()
        cache_stamp = (stat.st_mtime_ns, stat.st_size)
    else:
        cache_stamp = (-1, -1)
    cached = _aisle_config_cache.get(cache_key)
    if cached is not None and cached[0] == cache_stamp:
        return cached[1]

    if not resolved.exists():
        print(
            f"Warning: store aisle config not found ({resolved}); items will appear under Other.",
            file=sys.stderr,
        )

    config = parse_store_aisles_file(resolved)
    _aisle_config_cache[cache_key] = (cache_stamp, config)
    return config


def ingredient_name(item: str) -> str:
    """Return the ingredient name from a display line, stripping any amount prefix."""
    cleaned = strip_checklist_prefix(item)
    name, _amount = parse_amount(cleaned)
    return name or cleaned.strip()


# Free-text tails that are not part of the ingredient: ``butter for freezer``,
# ``cheese shredded!``, ``cauliflower head``.
_TRAILING_PUNCTUATION_RE = re.compile(r"[!?.\s]+$")
_FOR_PHRASE_RE = re.compile(r"\s+for\s+\S.*$", re.IGNORECASE)
_TRAILING_FORM_WORDS = frozenset(
    {"head", "heads", "shredded", "grated", "chopped", "sliced", "diced", "minced"}
)
_CAN_UNITS = frozenset({"can", "cans"})


def _strip_trailing_noise(name: str) -> str:
    """Drop trailing punctuation, ``for ...`` phrases, and form words like ``head``."""
    text = _TRAILING_PUNCTUATION_RE.sub("", name)
    text = _FOR_PHRASE_RE.sub("", text)
    words = text.split()
    while len(words) > 1 and words[-1] in _TRAILING_FORM_WORDS:
        words.pop()
    return " ".join(words)


def _strip_prep_suffix(name: str) -> str:
    """Remove trailing prep phrases so aisle keywords match the base ingredient."""
    text = name
    changed = True
    while changed:
        changed = False
        updated = _PREP_SUFFIX_RE.sub("", text).strip(" ,")
        if updated != text:
            text = updated
            changed = True
    return text


def _aisle_classification_name(item: str) -> str:
    """Ingredient name for keyword matching (keep phrases like ``bay leaves``)."""
    cleaned = strip_checklist_prefix(item)
    stripped = cleaned.strip().lower()
    name_part, _amount = parse_amount(cleaned)
    # ``parse_amount`` treats trailing ``leaves`` as a count unit (``2 leaves``).
    if stripped.endswith(" leaves") and len(stripped.split()) >= 2:
        base = stripped
    else:
        base = (name_part or stripped).lower()
    if _amount and _amount.split()[-1].lower() in _CAN_UNITS:
        base = f"canned {base}"
    return _strip_trailing_noise(_strip_prep_suffix(base))


def classify_aisle(item: str, *, config: StoreAisleConfig | None = None) -> str:
    """Classify a grocery list item into a store aisle."""
    cfg = config or load_store_aisles()
    name = _aisle_classification_name(item)
    if not name:
        return "other"

    name_words = name.split()

    product_aisle = _best_phrase_aisle(
        name_words,
        cfg.product_phrases,
        aisle_order=cfg.aisle_order,
    )
    if product_aisle is not None:
        return product_aisle

    multi_word = _best_keyword_aisle(
        name_words,
        cfg,
        min_keyword_words=2,
    )
    if multi_word is not None:
        return multi_word

    modifier_aisle = _aisle_from_modifiers(name_words)
    if modifier_aisle is not None:
        return modifier_aisle

    single_word = _best_keyword_aisle(
        name_words,
        cfg,
        min_keyword_words=1,
        max_keyword_words=1,
        single_word_head_only=True,
    )
    if single_word is not None:
        return single_word

    return "other"


def _aisle_from_modifiers(name_words: list[str]) -> str | None:
    """Route obvious form modifiers before single-token ingredient keywords."""
    if any(_word_matches(word, "frozen") for word in name_words):
        return "frozen"
    if any(_word_matches(word, "canned") for word in name_words):
        return "canned goods"
    return None


def _best_phrase_aisle(
    name_words: list[str],
    phrases: tuple[tuple[str, str], ...],
    *,
    aisle_order: tuple[str, ...],
) -> str | None:
    best_aisle: str | None = None
    best_phrase_len = 0
    best_aisle_rank = len(aisle_order)

    for phrase, aisle in phrases:
        phrase_words = phrase.split()
        if not _contains_word_phrase(name_words, phrase_words):
            continue
        phrase_len = len(phrase_words)
        rank = aisle_order.index(aisle) if aisle in aisle_order else len(aisle_order)
        if phrase_len > best_phrase_len or (
            phrase_len == best_phrase_len and rank < best_aisle_rank
        ):
            best_aisle = aisle
            best_phrase_len = phrase_len
            best_aisle_rank = rank

    return best_aisle


def _best_keyword_aisle(
    name_words: list[str],
    cfg: StoreAisleConfig,
    *,
    min_keyword_words: int,
    max_keyword_words: int | None = None,
    single_word_head_only: bool = False,
) -> str | None:
    best_aisle: str | None = None
    best_keyword_len = 0
    best_aisle_rank = len(cfg.aisle_order)

    for rank, aisle in enumerate(cfg.aisle_order):
        if aisle == "other":
            continue
        for keyword in cfg.aisle_keywords.get(aisle, ()):
            keyword_words = keyword.split()
            keyword_len = len(keyword_words)
            if keyword_len < min_keyword_words:
                continue
            if max_keyword_words is not None and keyword_len > max_keyword_words:
                continue
            if single_word_head_only and not _single_token_keyword_matches(
                name_words, keyword_words[0]
            ):
                continue
            if not _contains_word_phrase(name_words, keyword_words):
                continue
            if keyword_len > best_keyword_len or (
                keyword_len == best_keyword_len and rank < best_aisle_rank
            ):
                best_aisle = aisle
                best_keyword_len = keyword_len
                best_aisle_rank = rank

    return best_aisle


def _single_token_keyword_matches(name_words: list[str], keyword: str) -> bool:
    """Match single-token keywords on the full name or the head (last) word only."""
    if not name_words:
        return False
    if len(name_words) == 1:
        return _word_matches(name_words[0], keyword)
    return _word_matches(name_words[-1], keyword)


def sort_grocery_items(
    items: list[str],
    *,
    config: StoreAisleConfig | None = None,
) -> list[str]:
    """Sort grocery items by store walk order, then alphabetically within each aisle."""
    cfg = config or load_store_aisles()
    aisle_rank = {aisle: index for index, aisle in enumerate(cfg.aisle_order)}

    def sort_key(item: str) -> tuple[int, str]:
        aisle = classify_aisle(item, config=cfg)
        return aisle_rank.get(aisle, len(cfg.aisle_order)), item.lower()

    return sorted(items, key=sort_key)


def group_grocery_items_by_aisle(
    items: list[str],
    *,
    config: StoreAisleConfig | None = None,
) -> list[tuple[str, list[str]]]:
    """Group sorted grocery items by aisle, omitting empty aisles."""
    cfg = config or load_store_aisles()
    sorted_items = sort_grocery_items(items, config=cfg)
    groups: list[tuple[str, list[str]]] = []
    current_aisle: str | None = None
    current_items: list[str] = []

    for item in sorted_items:
        aisle = classify_aisle(item, config=cfg)
        if aisle != current_aisle:
            if current_items:
                groups.append((current_aisle or "other", current_items))
            current_aisle = aisle
            current_items = [item]
        else:
            current_items.append(item)

    if current_items:
        groups.append((current_aisle or "other", current_items))
    return groups


def aisle_label(aisle: str, *, config: StoreAisleConfig | None = None) -> str:
    cfg = config or load_store_aisles()
    return cfg.aisle_labels.get(aisle, aisle.title())


def is_legacy_notion_aisle_label(section: str | None) -> bool:
    """True when a Notion pantry aisle value predates a store-aisle taxonomy change."""
    if section is None or not str(section).strip():
        return False
    return str(section).strip().lower() in _LEGACY_NOTION_AISLE_LABELS


def resolve_pantry_aisle_id(
    section: str | None,
    *,
    config: StoreAisleConfig | None = None,
) -> str | None:
    """Map a pantry ``Section`` value to a store aisle id, or ``None`` if unset."""
    cfg = config or load_store_aisles()
    if section is None or not str(section).strip():
        return None
    raw = str(section).strip().lower()
    if raw in cfg.aisle_labels:
        return raw
    for aisle_id, label in cfg.aisle_labels.items():
        if label.strip().lower() == raw:
            return aisle_id
    if raw in ("uncategorized", "other"):
        return "other"
    return "other"


def pantry_aisle_for_item(
    item_name: str,
    section: str | None,
    *,
    config: StoreAisleConfig | None = None,
) -> str:
    """Aisle id for grouping a pantry item (stored section, else classify by name)."""
    cfg = config or load_store_aisles()
    stored = str(section).strip() if section is not None else ""
    if stored:
        if is_legacy_notion_aisle_label(stored):
            return classify_aisle(item_name, config=cfg)
        return resolve_pantry_aisle_id(stored, config=cfg) or "other"
    return classify_aisle(item_name, config=cfg)


def pantry_aisle_section_labels(*, config: StoreAisleConfig | None = None) -> list[str]:
    """Display labels for pantry Notion ``Section`` select options (store walk order)."""
    cfg = config or load_store_aisles()
    return [aisle_label(aisle_id, config=cfg) for aisle_id in cfg.aisle_order]


def canonical_pantry_section_label(
    section: str | None,
    *,
    aisle_id: str | None = None,
    config: StoreAisleConfig | None = None,
) -> str:
    """Notion select name for a pantry item's store aisle."""
    cfg = config or load_store_aisles()
    if aisle_id is not None:
        return aisle_label(aisle_id, config=cfg)
    resolved = resolve_pantry_aisle_id(section, config=cfg)
    if resolved is None:
        resolved = "other"
    return aisle_label(resolved, config=cfg)


def _contains_word_phrase(haystack_words: list[str], needle_words: list[str]) -> bool:
    if not needle_words or len(needle_words) > len(haystack_words):
        return False
    width = len(needle_words)
    for index in range(len(haystack_words) - width + 1):
        if all(
            _word_matches(haystack_words[index + offset], needle_words[offset])
            for offset in range(width)
        ):
            return True
    return False


def _word_matches(haystack_word: str, needle_word: str) -> bool:
    if haystack_word == needle_word:
        return True
    if haystack_word == needle_word + "s":
        return True
    if haystack_word == needle_word + "es":
        return True
    return needle_word.endswith("y") and haystack_word == needle_word[:-1] + "ies"
