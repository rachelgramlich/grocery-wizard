"""Reformat Notion ingredient text using the storage parser only (no URL fetch).

Use after parser/storage rules change. Reads each recipe's Ingredients column,
runs ``prepare_ingredients_for_notion``, and optionally writes back when safe.

See ``run_stored_ingredients_reformat`` for skip rules (unaccounted line-count drops,
would-drop lines, major edits).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from src.grocery_wizard.ingredients.parsed import (
    _is_citrus_zest_or_juice_only_line,
    format_ingredient_for_storage,
)
from src.grocery_wizard.ingredients.sync import (
    is_directive,
    is_instruction_line,
    is_junk_ingredient,
    is_metadata_line,
    prepare_ingredients_for_notion,
)
from src.grocery_wizard.integrations.notion import DatabaseSchema, NotionRecipesDB, Recipe
from src.grocery_wizard.recipes.recipe_maintenance import (
    FractionCallback,
    ProgressCallback,
    ingredients_text,
    recipe_has_link,
)


class ReformatStatus(StrEnum):
    UNCHANGED = "unchanged"
    APPLY_OK = "apply_ok"
    SKIP_NO_LINK = "skip_no_link"
    SKIP_EMPTY = "skip_empty"
    SKIP_LINE_COUNT = "skip_line_count"
    SKIP_WOULD_DROP = "skip_would_drop"
    SKIP_MAJOR_CHANGE = "skip_major_change"


@dataclass(slots=True)
class ReformatAnalysis:
    """Outcome of analyzing one recipe's stored ingredients."""

    status: ReformatStatus
    before: str
    after: str
    reasons: list[str] = field(default_factory=list)
    before_ingredient_line_count: int = 0
    after_ingredient_line_count: int = 0
    changed_line_count: int = 0


@dataclass(slots=True)
class ReformatSummary:
    scanned: int = 0
    unchanged: int = 0
    apply_ok: int = 0
    skipped: int = 0
    updated: int = 0
    failed: int = 0
    by_status: dict[str, int] = field(default_factory=dict)


def recipes_linked_with_ingredients(
    recipes: Sequence[Recipe],
    schema: DatabaseSchema,
) -> list[Recipe]:
    if not schema.ingredients_column:
        return []
    return [recipe for recipe in recipes if recipe_has_link(recipe) and ingredients_text(recipe)]


def _split_directives_and_ingredients(text: str) -> tuple[list[str], list[str]]:
    directives: list[str] = []
    ingredients: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if is_directive(line):
            directives.append(line)
        else:
            ingredients.append(line)
    return directives, ingredients


def _would_drop_before_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or is_directive(stripped):
        return False
    if is_metadata_line(stripped) or is_instruction_line(stripped) or is_junk_ingredient(stripped):
        return True
    if stripped.lower() == "recipe":
        return True
    return not format_ingredient_for_storage(stripped)


_AND_FRAGMENT_RE = re.compile(r"^and\b", re.IGNORECASE)
_CONTINUATION_FRAGMENT_RE = re.compile(
    r"^(?:"
    r"greens separated|green parts|pale green parts|light green parts|"
    r"in oil|syrup|maple|juices reserved|whites\b|white parts|"
    r"discarded|the rest drained|well stirred|at room temperature|"
    r"wedges(?:\s+for\s+serving)?|wheels for serving|washed,"
    r")",
    re.IGNORECASE,
)
_FOR_SERVING_RE = re.compile(r"\bfor serving\b", re.IGNORECASE)


def _is_intentional_drop_line(line: str) -> bool:
    """Lines we expect to lose when cleaning Notion ingredient blobs."""
    stripped = line.strip()
    if not stripped:
        return True
    if is_instruction_line(stripped) or is_metadata_line(stripped) or is_junk_ingredient(stripped):
        return True
    if _would_drop_before_line(stripped):
        return True
    if _is_citrus_zest_or_juice_only_line(stripped):
        return True
    if _AND_FRAGMENT_RE.match(stripped):
        return True
    if _CONTINUATION_FRAGMENT_RE.match(stripped):
        return True
    lowered = stripped.lower()
    if lowered.startswith("grated on "):
        return True
    if "crosswise into" in lowered:
        return True
    if _FOR_SERVING_RE.search(stripped):
        return True
    if lowered.endswith(")") and "(" not in stripped:
        return True
    if re.search(r",\s*zested\s*$", stripped, re.IGNORECASE):
        return True
    if re.search(r"\b(?:stems|stalks)\s+finely chopped\b", stripped, re.IGNORECASE):
        return True
    if re.search(r"\bwhites?\s*$", stripped, re.IGNORECASE) and "," in stripped:
        return True
    if stripped.lower().startswith("fresh herbs, such as"):
        return True
    if lowered.startswith(("seeds removed", "membrane removed")):
        return True
    if lowered.startswith(("juiced ", "juiced(")):
        return True
    if lowered.startswith("pestle,") or "spice grinder" in lowered:
        return True
    if lowered.startswith(("leaf ends trimmed", "leaf ends")):
        return True
    if lowered in {"drizzling", "membrane removed"}:
        return True
    if re.search(r"\bsee tip\b", lowered):
        return True
    if lowered in {"if you like", "if desired"}:
        return True
    return bool(re.match(r"^\d+\s+Pour\b", stripped))


def _comma_head_in_after(formatted: str, after_ingredients: Sequence[str]) -> bool:
    head = formatted.split(",", maxsplit=1)[0].strip().lower()
    if len(head) < 8:
        return False
    return any(head in after_line for after_line in after_ingredients)


def _or_alternative_tail_in_after(line: str, after_ingredients: Sequence[str]) -> bool:
    formatted = format_ingredient_for_storage(line.strip()).strip()
    after_lower = [part.strip().lower() for part in after_ingredients]
    for text in (formatted, line.strip()):
        if " or " not in text.lower():
            continue
        tail = re.split(r"\s+or\s+", text, maxsplit=0, flags=re.IGNORECASE)[-1].strip(" ,")
        tail_lower = tail.lower()
        if len(tail_lower) < 6:
            continue
        if any(tail_lower in after_line or after_line in tail_lower for after_line in after_lower):
            return True
    return False


def _before_line_accounted_in_after(line: str, after_ingredients: Sequence[str]) -> bool:
    """True when a before row is junk/prep or its storage form appears in after."""
    if _is_intentional_drop_line(line):
        return True
    formatted = format_ingredient_for_storage(line.strip()).strip()
    if not formatted:
        return True
    formatted_lower = formatted.lower()
    after_lower = [part.strip().lower() for part in after_ingredients]
    if formatted_lower in after_lower:
        return True
    if any(
        formatted_lower in after_line or after_line in formatted_lower for after_line in after_lower
    ):
        return True
    line_lower = line.strip().lower()
    if "lemon" in line_lower and any("lemon or lime" in after_line for after_line in after_lower):
        return True
    if (
        "lime" in line_lower
        and "juice" not in line_lower
        and any("lemon or lime" in after_line for after_line in after_lower)
    ):
        return True
    if _or_alternative_tail_in_after(line, after_ingredients):
        return True
    if _comma_head_in_after(formatted_lower, after_lower):
        return True
    return "fresh herbs (" in formatted_lower and any(
        "herb" in after_line or "cilantro" in after_line for after_line in after_lower
    )


def _line_count_drop_is_accounted(
    before_ingredients: Sequence[str],
    after_ingredients: Sequence[str],
) -> bool:
    if len(after_ingredients) >= len(before_ingredients):
        return True
    return all(
        _before_line_accounted_in_after(line, after_ingredients) for line in before_ingredients
    )


def analyze_stored_ingredient_reformat(before_text: str) -> ReformatAnalysis:
    """Dry-run one Ingredients blob; does not call Notion."""
    before = (before_text or "").strip()
    if not before:
        return ReformatAnalysis(
            status=ReformatStatus.SKIP_EMPTY,
            before=before_text or "",
            after="",
            reasons=["empty ingredients"],
        )

    after = prepare_ingredients_for_notion(before)
    if after.strip() == before:
        _, before_ing = _split_directives_and_ingredients(before)
        _, after_ing = _split_directives_and_ingredients(after)
        return ReformatAnalysis(
            status=ReformatStatus.UNCHANGED,
            before=before,
            after=after,
            before_ingredient_line_count=len(before_ing),
            after_ingredient_line_count=len(after_ing),
        )

    before_dirs, before_ing = _split_directives_and_ingredients(before)
    after_dirs, after_ing = _split_directives_and_ingredients(after)

    reasons: list[str] = []

    if len(after_ing) < len(before_ing) and not _line_count_drop_is_accounted(
        before_ing, after_ing
    ):
        reasons.append(
            f"ingredient line count dropped {len(before_ing)} → {len(after_ing)}",
        )
        unaccounted = [
            line for line in before_ing if not _before_line_accounted_in_after(line, after_ing)
        ]
        if unaccounted:
            reasons.append(f"unaccounted line(s), e.g. {unaccounted[0]!r}")
        return ReformatAnalysis(
            status=ReformatStatus.SKIP_LINE_COUNT,
            before=before,
            after=after,
            reasons=reasons,
            before_ingredient_line_count=len(before_ing),
            after_ingredient_line_count=len(after_ing),
        )

    drop_candidates = [
        line
        for line in before_ing
        if _would_drop_before_line(line) and not _before_line_accounted_in_after(line, after_ing)
    ]
    if drop_candidates:
        reasons.append(
            f"would drop {len(drop_candidates)} line(s), e.g. {drop_candidates[0]!r}",
        )
        return ReformatAnalysis(
            status=ReformatStatus.SKIP_WOULD_DROP,
            before=before,
            after=after,
            reasons=reasons,
            before_ingredient_line_count=len(before_ing),
            after_ingredient_line_count=len(after_ing),
        )

    changed = 0
    if len(before_ing) == len(after_ing):
        changed = sum(1 for b, a in zip(before_ing, after_ing, strict=True) if b != a)

    if before_dirs != after_dirs:
        reasons.append("directive lines would change")
        return ReformatAnalysis(
            status=ReformatStatus.SKIP_MAJOR_CHANGE,
            before=before,
            after=after,
            reasons=reasons,
            before_ingredient_line_count=len(before_ing),
            after_ingredient_line_count=len(after_ing),
            changed_line_count=changed,
        )

    return ReformatAnalysis(
        status=ReformatStatus.APPLY_OK,
        before=before,
        after=after,
        before_ingredient_line_count=len(before_ing),
        after_ingredient_line_count=len(after_ing),
        changed_line_count=changed,
    )


def analyze_recipe_reformat(recipe: Recipe) -> ReformatAnalysis:
    if not recipe_has_link(recipe):
        return ReformatAnalysis(
            status=ReformatStatus.SKIP_NO_LINK,
            before=ingredients_text(recipe),
            after="",
            reasons=["no link"],
        )
    return analyze_stored_ingredient_reformat(recipe.ingredients or "")


_COMPLEXITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("paren_ounce", re.compile(r"\(\s*\d+\s*-?\s*ounce", re.IGNORECASE)),
    ("sliced", re.compile(r"\bsliced\b", re.IGNORECASE)),
    ("crumbled", re.compile(r"\bcrumbled\b", re.IGNORECASE)),
    ("blocks", re.compile(r"\bblocks?\b", re.IGNORECASE)),
    ("remove_directive", re.compile(r"^remove\s*:", re.IGNORECASE | re.MULTILINE)),
    ("dual_measure", re.compile(r"\d+\s*/\s*\d+|\d+\s*grams", re.IGNORECASE)),
    ("cans", re.compile(r"\bcans?\b", re.IGNORECASE)),
    ("packed", re.compile(r"\bpacked\b", re.IGNORECASE)),
)


def score_ingredients_complexity(text: str) -> tuple[int, list[str]]:
    """Higher score = more interesting for dry-run samples."""
    score = 0
    tags: list[str] = []
    for name, pattern in _COMPLEXITY_PATTERNS:
        if pattern.search(text):
            score += 2
            tags.append(name)
    line_count = len([ln for ln in text.splitlines() if ln.strip()])
    score += min(line_count // 5, 4)
    return score, tags


def pick_showcase_recipes(
    recipes: Sequence[Recipe],
    schema: DatabaseSchema,
    *,
    limit: int = 6,
) -> list[tuple[Recipe, int, list[str]]]:
    candidates = recipes_linked_with_ingredients(recipes, schema)
    scored: list[tuple[int, Recipe, list[str]]] = []
    for recipe in candidates:
        analysis = analyze_stored_ingredient_reformat(recipe.ingredients or "")
        if analysis.status == ReformatStatus.UNCHANGED:
            continue
        score, tags = score_ingredients_complexity(recipe.ingredients or "")
        if analysis.status != ReformatStatus.APPLY_OK:
            score += 3
        scored.append((score, recipe, tags))
    scored.sort(key=lambda item: (-item[0], item[1].name.casefold()))
    return [(r, s, t) for s, r, t in scored[:limit]]


def write_reformat_csv(
    path: Path,
    rows: Sequence[tuple[Recipe, ReformatAnalysis]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "page_id",
                "name",
                "link",
                "status",
                "reasons",
                "before",
                "after",
                "before_line_count",
                "after_line_count",
                "changed_lines",
            ],
        )
        for recipe, analysis in rows:
            writer.writerow(
                [
                    recipe.page_id,
                    recipe.name,
                    recipe.link or "",
                    analysis.status.value,
                    "; ".join(analysis.reasons),
                    analysis.before,
                    analysis.after,
                    analysis.before_ingredient_line_count,
                    analysis.after_ingredient_line_count,
                    analysis.changed_line_count,
                ],
            )


def run_stored_ingredients_reformat(
    db: NotionRecipesDB,
    candidates: Sequence[Recipe],
    *,
    dry_run: bool = True,
    batch_size: int = 20,
    export_csv_path: Path | None = None,
    on_progress: ProgressCallback | None = None,
    on_fraction: FractionCallback | None = None,
) -> ReformatSummary:
    schema = db.schema
    summary = ReformatSummary(scanned=len(candidates))
    if not schema.ingredients_column:
        summary.skipped = len(candidates)
        return summary

    analyses: list[tuple[Recipe, ReformatAnalysis]] = []
    total = len(candidates)

    for index, recipe in enumerate(candidates, start=1):
        if on_fraction and total:
            on_fraction(index / total)

        analysis = analyze_recipe_reformat(recipe)
        analyses.append((recipe, analysis))
        summary.by_status[analysis.status.value] = (
            summary.by_status.get(analysis.status.value, 0) + 1
        )

        if analysis.status == ReformatStatus.UNCHANGED:
            summary.unchanged += 1
            if on_progress:
                on_progress(f"Unchanged: {recipe.name}")
            continue

        if analysis.status == ReformatStatus.APPLY_OK:
            summary.apply_ok += 1
            if dry_run:
                summary.skipped += 1
                if on_progress:
                    on_progress(f"Would update: {recipe.name}")
                continue
            try:
                db.update_recipe(
                    recipe.page_id,
                    {schema.ingredients_column: analysis.after},
                )
                summary.updated += 1
                if on_progress:
                    on_progress(f"Updated: {recipe.name}")
            except Exception as exc:
                summary.failed += 1
                if on_progress:
                    on_progress(f"Failed: {recipe.name} — {exc}")
            continue

        summary.skipped += 1
        detail = analysis.reasons[0] if analysis.reasons else analysis.status.value
        if on_progress:
            on_progress(f"Skipped ({analysis.status.value}): {recipe.name} — {detail}")

    if export_csv_path is not None:
        write_reformat_csv(export_csv_path, analyses)

    if on_fraction:
        on_fraction(1.0)
    return summary


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reformat Notion recipe ingredients from stored text only (no URL fetch).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write safe updates to Notion (default is dry-run only).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Max recipes per run (default 20).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip this many linked recipes with ingredients before batching.",
    )
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=None,
        help="CSV path for before/after (default: reformat_ingredients_<timestamp>.csv).",
    )
    parser.add_argument(
        "--showcase",
        type=int,
        default=0,
        metavar="N",
        help="Print before/after for N complex recipes (dry-run analysis only).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    from src.grocery_wizard.config import load_config

    args = _parse_args(argv)
    cfg = load_config()
    db = NotionRecipesDB(cfg)
    recipes = db.query_recipes()
    schema = db.schema
    linked = recipes_linked_with_ingredients(recipes, schema)
    batch = linked[args.offset : args.offset + args.batch_size]

    if args.showcase:
        picks = pick_showcase_recipes(recipes, schema, limit=args.showcase)
        for recipe, score, tags in picks:
            analysis = analyze_recipe_reformat(recipe)
            print(f"\n=== {recipe.name} (score={score}, tags={', '.join(tags) or '—'}) ===")
            print(f"Status: {analysis.status.value}")
            if analysis.reasons:
                print(f"Reasons: {'; '.join(analysis.reasons)}")
            print("--- BEFORE ---")
            print(analysis.before)
            print("--- AFTER ---")
            print(analysis.after or "(empty)")
        if not args.apply and not batch:
            return 0

    export_path = args.export_csv
    if export_path is None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        export_path = Path(f"reformat_ingredients_{stamp}.csv")

    dry_run = not args.apply
    mode = "dry-run" if dry_run else "apply"
    print(
        f"{mode}: {len(batch)} recipe(s) (offset {args.offset}, "
        f"batch-size {args.batch_size}, {len(linked)} linked with ingredients total)",
        file=sys.stderr,
    )

    def on_progress(message: str) -> None:
        print(message, file=sys.stderr)

    summary = run_stored_ingredients_reformat(
        db,
        batch,
        dry_run=dry_run,
        batch_size=args.batch_size,
        export_csv_path=export_path,
        on_progress=on_progress,
    )
    print(f"CSV: {export_path.resolve()}", file=sys.stderr)
    print(
        f"scanned={summary.scanned} unchanged={summary.unchanged} "
        f"apply_ok={summary.apply_ok} updated={summary.updated} "
        f"skipped={summary.skipped} failed={summary.failed} "
        f"by_status={summary.by_status}",
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
