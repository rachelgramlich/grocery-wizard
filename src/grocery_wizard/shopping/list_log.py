"""Debug log for each built grocery list.

Each build writes one JSON debug record to Notion (household database) and optionally
mirrors the newest files under ``LIST_HISTORY_DIR`` on the host running Streamlit.

``ListTrace`` is filled while the list is built; ``build_list_log`` turns it into the
JSON-ready dict; ``write_list_log`` saves it and keeps only the newest files.
"""

from __future__ import annotations

__all__ = [
    "LIST_LOG_SCHEMA_VERSION",
    "MAX_LIST_LOGS",
    "ListTrace",
    "apply_adjustments",
    "build_list_log",
    "dump_list_log",
    "latest_list_log_path",
    "rewrite_list_log",
    "write_list_log",
]

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.grocery_wizard.config import LIST_HISTORY_DIR
from src.grocery_wizard.ingredients.sync import apply_removals, parse_ingredients_text
from src.grocery_wizard.shopping.grocery_list import _normalized_item_key
from src.grocery_wizard.shopping.store_aisles import aisle_label, classify_aisle

LIST_LOG_SCHEMA_VERSION = 1
MAX_LIST_LOGS = 20

OUTCOME_KEPT = "kept"
OUTCOME_PANTRY = "skipped_pantry"
OUTCOME_UNPARSED = "skipped_unparsed"
OUTCOME_REMOVAL_DIRECTIVE = "skipped_removal_directive"

SOURCE_RECIPE = "recipe"
SOURCE_RECURRING = "recurring"
SOURCE_STAPLE = "staple"
SOURCE_EXTRA = "extra"
SOURCE_PANTRY_READD = "pantry_readd"
SOURCE_UNKNOWN = "unknown"

_LOG = logging.getLogger(__name__)


@dataclass
class _RecipeTrace:
    name: str
    ingredient_source: str
    raw_lines: list[str]
    removal_directives: list[str]


@dataclass
class ListTrace:
    """Facts collected while ``build_grocery_list`` runs (nothing here changes the list)."""

    recipes: list[_RecipeTrace] = field(default_factory=list)
    lines: list[dict[str, Any]] = field(default_factory=list)
    recurring_added: list[str] = field(default_factory=list)
    staples_added: list[str] = field(default_factory=list)

    def start_recipe(self, name: str, text: str | None, *, ingredient_source: str) -> None:
        """Record a recipe's raw ingredient lines and lines dropped by ``remove:`` directives."""
        raw_lines, removals = parse_ingredients_text(text or "")
        kept = apply_removals(raw_lines, removals)
        self.recipes.append(
            _RecipeTrace(
                name=name,
                ingredient_source=ingredient_source,
                raw_lines=raw_lines,
                removal_directives=removals,
            )
        )
        remaining = list(kept)
        for raw in raw_lines:
            if raw in remaining:
                remaining.remove(raw)
                continue
            self.record_line(name, raw, outcome=OUTCOME_REMOVAL_DIRECTIVE)

    def record_line(
        self,
        recipe: str | None,
        raw: str,
        *,
        outcome: str,
        item: str | None = None,
        amount: str | None = None,
    ) -> None:
        self.lines.append(
            {
                "recipe": recipe,
                "raw": raw,
                "item": item,
                "amount": amount,
                "outcome": outcome,
            }
        )


def _source_for_item(
    line: str,
    *,
    recipes_by_key: dict[str, list[str]],
    recurring_keys: set[str],
    staple_keys: set[str],
    extra_keys: set[str],
    readd_keys: set[str],
) -> tuple[str, list[str]]:
    key = _normalized_item_key(line)
    if key in recipes_by_key:
        return SOURCE_RECIPE, recipes_by_key[key]
    for kind, keys in (
        (SOURCE_PANTRY_READD, readd_keys),
        (SOURCE_RECURRING, recurring_keys),
        (SOURCE_STAPLE, staple_keys),
        (SOURCE_EXTRA, extra_keys),
    ):
        if key in keys:
            return kind, []
    return SOURCE_UNKNOWN, []


def _final_list_entries(
    final_items: list[str],
    *,
    item_provenance: dict[str, list[str]],
    recurring_added: list[str],
    staples_added: list[str],
    extra_items: list[str],
    readd: list[str],
) -> list[dict[str, Any]]:
    recipes_by_key = {
        _normalized_item_key(item): recipes for item, recipes in item_provenance.items()
    }
    keys = {
        "recurring_keys": {_normalized_item_key(item) for item in recurring_added},
        "staple_keys": {_normalized_item_key(item) for item in staples_added},
        "extra_keys": {_normalized_item_key(item) for item in extra_items},
        "readd_keys": {_normalized_item_key(item) for item in readd},
    }
    entries: list[dict[str, Any]] = []
    for line in final_items:
        source, recipes = _source_for_item(line, recipes_by_key=recipes_by_key, **keys)
        aisle = classify_aisle(line)
        entries.append(
            {
                "item": line,
                "aisle": aisle_label(aisle),
                "source": source,
                "recipes": list(recipes),
            }
        )
    return entries


def build_list_log(
    trace: ListTrace,
    *,
    meals: list[str],
    exclude_pantry: bool,
    excluded_pantry: list[str],
    missing_ingredients: list[str],
    item_provenance: dict[str, list[str]],
    extra_items: list[str],
    final_items: list[str],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """JSON-ready log for one build (``final_items`` is the list the user sees first)."""
    traces_by_name = {recipe.name: recipe for recipe in trace.recipes}
    meal_entries = []
    for name in meals:
        recipe = traces_by_name.get(name)
        meal_entries.append(
            {
                "name": name,
                "ingredient_source": recipe.ingredient_source if recipe else None,
                "raw_lines": list(recipe.raw_lines) if recipe else [],
                "removal_directives": list(recipe.removal_directives) if recipe else [],
            }
        )
    skipped = [
        {
            "recipe": entry["recipe"],
            "line": entry["raw"],
            "item": entry["item"],
            "reason": entry["outcome"].removeprefix("skipped_"),
        }
        for entry in trace.lines
        if entry["outcome"] != OUTCOME_KEPT
    ]
    return {
        "schema_version": LIST_LOG_SCHEMA_VERSION,
        "created_at": (created_at or datetime.now(UTC)).isoformat(),
        "options": {"exclude_pantry": exclude_pantry},
        "meals": meal_entries,
        "missing_ingredients": list(missing_ingredients),
        "parsed_lines": list(trace.lines),
        "skipped": skipped,
        "pantry_excluded": list(excluded_pantry),
        "recurring_added": list(trace.recurring_added),
        "staples_added": list(trace.staples_added),
        "extra_items": list(extra_items),
        "final_list": _final_list_entries(
            final_items,
            item_provenance=item_provenance,
            recurring_added=trace.recurring_added,
            staples_added=trace.staples_added,
            extra_items=extra_items,
            readd=[],
        ),
        "user_adjustments": {"pantry_readded": [], "removed_once": []},
    }


def apply_adjustments(
    log: dict[str, Any],
    *,
    final_items: list[str],
    readd: list[str],
    removed_once: list[str],
) -> dict[str, Any]:
    """Copy of *log* with the post-build "Adjust this week's list" choices applied."""
    previous = {_normalized_item_key(entry["item"]): entry for entry in log["final_list"]}
    readd_keys = {_normalized_item_key(item) for item in readd}
    entries: list[dict[str, Any]] = []
    for line in final_items:
        key = _normalized_item_key(line)
        old = previous.get(key)
        if old is not None:
            entries.append({**old, "item": line})
            continue
        source = SOURCE_PANTRY_READD if key in readd_keys else SOURCE_UNKNOWN
        entries.append(
            {
                "item": line,
                "aisle": aisle_label(classify_aisle(line)),
                "source": source,
                "recipes": [],
            }
        )
    return {
        **log,
        "final_list": entries,
        "user_adjustments": {
            "pantry_readded": list(readd),
            "removed_once": list(removed_once),
        },
    }


def _history_dir(history_dir: Path | None) -> Path:
    return history_dir if history_dir is not None else LIST_HISTORY_DIR


def _log_filename(created_at: str) -> str:
    stamp = datetime.fromisoformat(created_at).astimezone(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    return f"{stamp}.json"


def dump_list_log(log: dict[str, Any]) -> str:
    """Serialize a log dict for JSON files and Notion ``Log JSON`` columns."""
    return json.dumps(log, indent=2, ensure_ascii=False) + "\n"


def _dump(log: dict[str, Any]) -> str:
    return dump_list_log(log)


def write_list_log(
    log: dict[str, Any],
    *,
    history_dir: Path | None = None,
    keep: int = MAX_LIST_LOGS,
) -> Path | None:
    """Save *log* as a new file, delete older ones beyond *keep*. Never raises on disk errors."""
    directory = _history_dir(history_dir)
    path = directory / _log_filename(log["created_at"])
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(log), encoding="utf-8")
        for old in sorted(directory.glob("*.json"))[: -max(keep, 1)]:
            old.unlink(missing_ok=True)
    except OSError:
        _LOG.warning("Could not write grocery list debug log to %s", path, exc_info=True)
        return None
    return path


def rewrite_list_log(path: Path, log: dict[str, Any]) -> bool:
    """Overwrite an existing log file (used after the user adjusts the list)."""
    try:
        path.write_text(_dump(log), encoding="utf-8")
    except OSError:
        _LOG.warning("Could not update grocery list debug log at %s", path, exc_info=True)
        return False
    return True


def latest_list_log_path(history_dir: Path | None = None) -> Path | None:
    directory = _history_dir(history_dir)
    if not directory.is_dir():
        return None
    files = sorted(directory.glob("*.json"))
    return files[-1] if files else None
