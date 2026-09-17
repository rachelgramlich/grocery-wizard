"""Dev / maintenance CLI commands."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from src.grocery_wizard.config import load_config
from src.grocery_wizard.integrations.notion import NotionRecipesDB

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register_dev_commands(dev_subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    backfill_parser = dev_subparsers.add_parser(
        "backfill-ingredients",
        help="Fill in missing ingredient lists from recipe links",
    )
    backfill_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which recipes would be updated without writing to Notion",
    )
    backfill_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape recipes with empty ingredients (does not overwrite filled rows)",
    )
    backfill_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show each scraped ingredient line as it is saved",
    )
    backfill_parser.set_defaults(func=cmd_dev_backfill)

    reconcile_parser = dev_subparsers.add_parser(
        "reconcile-ingredients",
        help="Update ingredients where you already have some (keeps your edits)",
    )
    reconcile_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which recipes would be merged without writing to Notion",
    )
    reconcile_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show each scraped ingredient line during merge",
    )
    reconcile_parser.set_defaults(func=cmd_dev_reconcile)

    refresh_parser = dev_subparsers.add_parser(
        "refresh-all-ingredients",
        help="Re-download ingredients for every recipe",
    )
    refresh_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to Notion",
    )
    refresh_parser.add_argument(
        "--split-only",
        action="store_true",
        help="Re-split existing ingredient text without re-scraping links",
    )
    refresh_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show ingredient lines for each recipe",
    )
    refresh_parser.add_argument(
        "--recipe",
        metavar="NAME",
        help="Only refresh recipes whose Notion name contains this substring (case-insensitive)",
    )
    refresh_parser.set_defaults(func=cmd_dev_refresh_all)

    reformat_parser = dev_subparsers.add_parser(
        "reformat-ingredients",
        help="Clean up stored ingredient text (split compounds, drop junk)",
    )
    reformat_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to Notion",
    )
    reformat_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show ingredient lines for each recipe",
    )
    reformat_parser.add_argument(
        "--recipe",
        metavar="NAME",
        help="Only reformat recipes whose Notion name contains this substring (case-insensitive)",
    )
    reformat_parser.set_defaults(func=cmd_dev_reformat)

    audit_parser = dev_subparsers.add_parser(
        "audit-recipes",
        help="Show which recipes need attention",
    )
    audit_parser.set_defaults(func=cmd_dev_audit)

    schema_parser = dev_subparsers.add_parser(
        "show-schema",
        help="Show how Notion columns are detected",
    )
    schema_parser.set_defaults(func=cmd_dev_schema)

    sync_pantry_parser = dev_subparsers.add_parser(
        "sync-notion-pantry-sections",
        help="Set pantry Section select options from config/store_aisles.txt",
    )
    sync_pantry_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without calling Notion",
    )
    sync_pantry_parser.set_defaults(func=cmd_dev_sync_notion_pantry_sections)

    remap_pantry_parser = dev_subparsers.add_parser(
        "remap-notion-pantry-aisles",
        help="Set each pantry row's Aisle from store_aisles keyword rules on the item name",
    )
    remap_pantry_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without calling Notion",
    )
    remap_pantry_parser.set_defaults(func=cmd_dev_remap_notion_pantry_aisles)

    list_feedback_parser = dev_subparsers.add_parser(
        "list-feedback",
        help="Show feedback collected from production commands",
    )
    list_feedback_parser.set_defaults(func=cmd_dev_list_feedback)

    validate_pipeline_parser = dev_subparsers.add_parser(
        "validate-pipeline",
        help="Run Notion → meal plan → grocery list validation report",
    )
    validate_pipeline_parser.add_argument(
        "--seeds",
        default="1,2,3",
        help="Comma-separated random seeds for suggest_meals (default: 1,2,3)",
    )
    validate_pipeline_parser.add_argument(
        "--meals",
        type=int,
        default=None,
        help="Meal count when no saved week plan exists (default: from config)",
    )
    validate_pipeline_parser.add_argument(
        "--output",
        default=".local/pipeline_validation_report.txt",
        help="Where to write the report (default: .local/pipeline_validation_report.txt)",
    )
    validate_pipeline_parser.add_argument(
        "--suggest-meals",
        action="store_true",
        help="Ignore saved week plan and use suggest_meals with --seeds",
    )
    validate_pipeline_parser.set_defaults(func=cmd_dev_validate_pipeline)

    suggest_fixes_parser = dev_subparsers.add_parser(
        "suggest-fixes",
        help="Analyse ingredient edit log and suggest junk phrase additions",
    )
    suggest_fixes_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output raw aggregated data as JSON instead of a human-readable report",
    )
    suggest_fixes_parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        metavar="N",
        help="Minimum removal count to include a phrase in suggestions (default: 2)",
    )
    suggest_fixes_parser.set_defaults(func=cmd_dev_suggest_fixes)

    create_issues_parser = dev_subparsers.add_parser(
        "create-issues",
        help="Plan and open GitHub issue(s) from one or more notes (bug vs backlog auto)",
    )
    create_issues_parser.add_argument(
        "items",
        nargs="*",
        help="Freeform notes (or omit and pass --item / --plan-file / stdin)",
    )
    create_issues_parser.add_argument(
        "--item",
        action="append",
        dest="item_flags",
        default=[],
        metavar="TEXT",
        help="Repeat for each note; grouped by code area and kind",
    )
    create_issues_parser.add_argument(
        "--plan-file",
        metavar="PATH",
        help="JSON array of planned issues (from --dry-run --json); skips auto-planning",
    )
    create_issues_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print grouping plan without creating issues",
    )
    create_issues_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="With --dry-run: emit planned issues as JSON for --plan-file",
    )
    create_issues_parser.add_argument(
        "--audit",
        action="store_true",
        help="Label created issues with audit (architecture / standards follow-ups)",
    )
    create_issues_parser.set_defaults(func=cmd_dev_create_issues)

    list_enh_parser = dev_subparsers.add_parser(
        "list-enhancements",
        help="List open enhancement issues (label grocery-wizard)",
    )
    list_enh_parser.add_argument(
        "--all",
        action="store_true",
        dest="include_closed",
        help="Include closed/done enhancements",
    )
    list_enh_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output raw JSONL",
    )
    list_enh_parser.set_defaults(func=cmd_dev_list_enhancements)

    work_issue_parser = dev_subparsers.add_parser(
        "work-on-issue",
        help="Full agent brief for a backlog item or bug issue",
    )
    work_issue_parser.add_argument(
        "id",
        help="GitHub issue number (#74 or 74)",
    )
    work_issue_parser.set_defaults(func=cmd_dev_work_on_issue)

    manual_ver_parser = dev_subparsers.add_parser(
        "record-manual-verification",
        help="Post manual UAT sign-off comment on the PR (after user confirms)",
    )
    manual_ver_parser.add_argument("id", help="GitHub issue number (e.g. 96)")
    manual_ver_parser.add_argument(
        "--pr-url",
        default="",
        help="PR URL (default: current branch via gh pr view)",
    )
    manual_ver_parser.add_argument(
        "--note",
        default="",
        help="Optional extra detail for the PR comment",
    )
    manual_ver_parser.set_defaults(func=cmd_dev_record_manual_verification)

    pr_title_parser = dev_subparsers.add_parser(
        "enhancement-pr-title",
        help="Print the standard PR title for an enhancement",
    )
    pr_title_parser.add_argument("id", help="GitHub issue number (e.g. 96)")
    pr_title_parser.set_defaults(func=cmd_dev_enhancement_pr_title)

    migrate_enh_parser = dev_subparsers.add_parser(
        "migrate-enhancements-to-github",
        help="One-time import from legacy enhancements.jsonl into GitHub Issues",
    )
    migrate_enh_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be imported without creating issues",
    )
    migrate_enh_parser.set_defaults(func=cmd_dev_migrate_enhancements_to_github)

    backfill_labels_parser = dev_subparsers.add_parser(
        "backfill-enhancement-labels",
        help="Add grocery-wizard label to legacy title-matched backlog issues",
    )
    backfill_labels_parser.add_argument(
        "--strip-title-prefix",
        action="store_true",
        help="Remove [Grocery Wizard] / Grocery Wizard: from issue titles",
    )
    backfill_labels_parser.set_defaults(func=cmd_dev_backfill_enhancement_labels)


def cmd_dev_sync_notion_pantry_sections(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.notion_pantry_setup import sync_pantry_section_store_aisles

    try:
        result = sync_pantry_section_store_aisles(dry_run=args.dry_run)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    mode = "Dry run —" if args.dry_run else "Updated"
    print(f"{mode} pantry Aisle/Section property was {result.previous_type!r}")
    print(f"Select options ({len(result.aisle_labels)}): {', '.join(result.aisle_labels)}")
    if args.dry_run:
        print(f"Would remap {result.rows_migrated} pantry row(s) by item name.")
    else:
        print(f"Remapped {result.rows_migrated} pantry row(s) by item name.")
    return 0


def cmd_dev_remap_notion_pantry_aisles(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.notion_pantry_setup import (
        remap_pantry_aisles_from_item_names,
    )

    try:
        result = remap_pantry_aisles_from_item_names(dry_run=args.dry_run)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    prefix = "Would update" if args.dry_run else "Updated"
    print(f"{prefix} {result.rows_updated} row(s); {result.rows_unchanged} already correct.")
    for label in sorted(result.by_aisle):
        print(f"  {label}: {result.by_aisle[label]}")
    return 0


def cmd_dev_schema(_args: argparse.Namespace) -> int:
    config = load_config()
    db = NotionRecipesDB(config)
    schema = db.schema

    print(f"Recipes database ID: {config.notion_recipe_database_id}")
    print(f"Name column: {schema.name_column}")
    print(f"Link column: {schema.link_column}")
    print(f"Ingredients column: {schema.ingredients_column or '(not detected)'}")
    print()

    print("All columns:")
    for name, col in sorted(schema.all_columns.items()):
        line = f"  {name} ({col.type})"
        if col.options:
            line += f" — options: {', '.join(col.options)}"
        print(line)

    print()
    print(f"Filter columns ({len(schema.filter_columns)}):")
    for col in schema.filter_columns:
        print(f"  {col.name} ({col.type})")
        if col.options:
            print(f"    options: {', '.join(col.options)}")

    recipes = db.query_recipes()
    print()
    print(f"Recipes in database: {len(recipes)}")
    return 0


def _dev_batch_ingredients_removed(command: str) -> int:
    print(f"Command 'dev {command}' was removed.", file=sys.stderr)
    print(
        "Use the Streamlit app (`just grocery-ui`) — **Add Recipe** tab or edit "
        "ingredients in Notion.",
        file=sys.stderr,
    )
    return 1


def cmd_dev_backfill(_args: argparse.Namespace) -> int:
    return _dev_batch_ingredients_removed("backfill-ingredients")


def cmd_dev_reconcile(_args: argparse.Namespace) -> int:
    return _dev_batch_ingredients_removed("reconcile-ingredients")


def cmd_dev_refresh_all(_args: argparse.Namespace) -> int:
    return _dev_batch_ingredients_removed("refresh-all-ingredients")


def cmd_dev_reformat(args: argparse.Namespace) -> int:
    """Re-run ingest cleanup on stored Notion ingredients without re-scraping."""
    args.split_only = True
    return cmd_dev_refresh_all(args)


def cmd_dev_audit(_args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.audit import audit_recipes, format_audit_report

    config = load_config()
    db = NotionRecipesDB(config)
    report = audit_recipes(db.query_recipes())
    print(format_audit_report(report))
    return 0


def cmd_dev_list_feedback(_args: argparse.Namespace) -> int:
    from src.grocery_wizard.lib.feedback import list_feedback

    print(list_feedback())
    return 0


def cmd_dev_validate_pipeline(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.validate_pipeline import (
        format_pipeline_report,
        run_pipeline_validation,
    )

    config = load_config()
    db = NotionRecipesDB(config)

    seed_values: list[int | None]
    if args.seeds.strip().lower() in ("none", "saved"):
        seed_values = [None]
    else:
        seed_values = [int(part.strip()) for part in args.seeds.split(",") if part.strip()]

    output_path = Path(args.output)
    report = run_pipeline_validation(
        db,
        meals=args.meals,
        seeds=seed_values,
        use_saved_week_plan=not args.suggest_meals,
    )
    text = format_pipeline_report(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nReport saved to {output_path}")
    return 0


def cmd_dev_suggest_fixes(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.edit_log import EDIT_LOG_PATH

    log_path = Path(EDIT_LOG_PATH)
    if not log_path.exists() or log_path.stat().st_size == 0:
        if args.output_json:
            print(json.dumps({"phrases": [], "recipe_map": {}}))
        else:
            print("No ingredient edit log found.")
            print(f"Expected: {log_path}")
            print("Edits are logged automatically when you save changes in the review UI.")
        return 0

    removal_counts: Counter[str] = Counter()
    recipe_map: dict[str, list[str]] = defaultdict(list)

    with log_path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            recipe = entry.get("recipe_name", "unknown")
            for removed in entry.get("removed_lines", []):
                removal_counts[removed] += 1
                if recipe not in recipe_map[removed]:
                    recipe_map[removed].append(recipe)

    min_count = args.min_count
    candidates = [
        {"phrase": phrase, "count": count, "recipes": sorted(recipe_map[phrase])}
        for phrase, count in removal_counts.most_common()
        if count >= min_count
    ]

    if args.output_json:
        print(json.dumps({"min_count": min_count, "phrases": candidates}, indent=2))
        return 0

    if not candidates:
        print(f"No ingredient lines removed {min_count}+ times yet.")
        total_removals = sum(removal_counts.values())
        unique_lines = len(removal_counts)
        print(f"(Log has {total_removals} total removals across {unique_lines} unique lines.)")
        return 0

    print("=" * 70)
    print("SECTION 1 — Suggested junk phrase additions")
    print("=" * 70)
    print()
    print("Lines removed most often across all sessions (paste into")
    print("_JUNK_ONLY_PHRASES in src/grocery_wizard/ingredients/_patterns.py):")
    print()
    for c in candidates:
        print(f"    {c['phrase']!r},  # removed {c['count']}x")

    print()
    print("=" * 70)
    print("SECTION 2 — Suggested Notion cleanup")
    print("=" * 70)
    print()
    print("Recipes containing each suggested junk phrase (re-clean these in Notion):")
    print()
    for c in candidates:
        recipes_str = ", ".join(c["recipes"]) if c["recipes"] else "(no recipe recorded)"
        print(f"  {c['phrase']!r}  →  {recipes_str}")

    print()
    print("=" * 70)
    print("SECTION 3 — How to create a PR")
    print("=" * 70)
    print()
    print("Step-by-step instructions:")
    print()
    print("  a) Add phrases to _JUNK_ONLY_PHRASES in")
    print("     src/grocery_wizard/ingredients/_patterns.py")
    print()
    print("  b) Strip those lines from Notion entries:")
    print()
    print("     uv run python -m src.grocery_wizard.cli dev reformat-ingredients --dry-run")
    print("     # Review the above, then run without --dry-run:")
    print("     uv run python -m src.grocery_wizard.cli dev reformat-ingredients")
    print()
    print("  c) Commit and push:")
    print()
    branch = "cursor/add-junk-phrases-XXXX"
    pr_title = f"fix(ingredients): add {len(candidates)} junk phrase(s) to parser patterns"
    pr_body = (
        "## Summary\\n\\n"
        f"Adds {len(candidates)} frequently-removed ingredient line(s) to `_JUNK_ONLY_PHRASES` "
        "in `_patterns.py` based on user edit-log analysis.\\n\\n"
        "## Phrases added\\n\\n"
        + "\\n".join(f"- `{c['phrase']}`" for c in candidates)
        + "\\n\\n## Testing\\n\\n"
        "- [ ] `uv run pytest` passes\\n"
        "- [ ] `dev reformat-ingredients` strips affected lines from Notion\\n"
    )
    print(f"     git checkout -b {branch}")
    print("     # (edit _patterns.py as described above)")
    print("     git add src/grocery_wizard/ingredients/_patterns.py")
    print(f"     git commit -m {pr_title!r}")
    print(f"     git push -u origin {branch}")
    print("     gh pr create \\")
    print(f"       --title {pr_title!r} \\")
    print(f"       --body {pr_body!r}")
    print()

    return 0


def cmd_dev_create_issues(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import create_planned_issues
    from src.grocery_wizard.dev.issue_planning import (
        plan_from_items,
        planned_issue_from_dict,
        planned_issue_to_dict,
    )

    if args.plan_file:
        path = Path(args.plan_file)
        if not path.exists():
            print(f"Plan file not found: {path}", file=sys.stderr)
            return 1
        raw_plan = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_plan, list):
            print("Plan file must be a JSON array.", file=sys.stderr)
            return 1
        planned = [planned_issue_from_dict(row) for row in raw_plan]
    else:
        notes = list(args.items) + list(args.item_flags or [])
        if not notes and not sys.stdin.isatty():
            stdin_text = sys.stdin.read()
            notes = [block.strip() for block in stdin_text.split("\n\n") if block.strip()]
            if len(notes) == 1 and "\n" in notes[0]:
                notes = [line.strip() for line in notes[0].splitlines() if line.strip()]
        if not notes:
            print(
                "Provide notes as arguments, --item (repeat), stdin paragraphs, or --plan-file.",
                file=sys.stderr,
            )
            return 1
        planned = plan_from_items(notes)

    if args.audit:
        for issue in planned:
            issue.audit = True

    if not planned:
        print("Nothing to create.", file=sys.stderr)
        return 1

    if args.dry_run:
        if args.output_json:
            print(json.dumps([planned_issue_to_dict(p) for p in planned], indent=2))
            return 0
        print(f"Would create {len(planned)} issue(s):\n")
        for index, issue in enumerate(planned, start=1):
            items_note = (
                f" ({len(issue.source_items)} notes merged)"
                if len(issue.source_items) > 1
                else ""
            )
            audit_note = " audit=yes" if issue.audit else ""
            print(f"{index}. [{issue.kind}] area={issue.area}{audit_note}{items_note}")
            print(f"   title: {issue.title}")
        return 0

    created = create_planned_issues(planned, dry_run=False)
    for row in created:
        kind = row.get("kind", "?")
        num = row.get("issue_number")
        ref = f"#{num}" if num else "?"
        url = row.get("issue_url") or ""
        print(f"Created {kind} {ref}: {row.get('title', '')}")
        if url:
            print(f"  {url}")
    return 0


def cmd_dev_list_enhancements(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import list_enhancements

    entries = list_enhancements(include_closed=args.include_closed)

    if args.output_json:
        for entry in entries:
            print(json.dumps(entry))
        return 0

    if not entries:
        print("No enhancements found.")
        return 0

    for entry in entries:
        area = entry.get("area", "other")
        num = entry.get("issue_number") or entry.get("id", "?")
        title = entry.get("title", "")
        status = entry.get("status", "open")
        status_tag = f" [{status}]" if status != "open" else ""
        issue_url = entry.get("issue_url", "")
        pr_url = entry.get("pr_url", "")
        link = pr_url or issue_url
        link_tag = f" → {link}" if link else ""
        print(f"#{num} [{area}] {title}{status_tag}{link_tag}")
    return 0


def cmd_dev_work_on_issue(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import format_work_prompt, get_work_item

    entry = get_work_item(args.id)
    if entry is None:
        print(
            f"Issue '{args.id}' not found (backlog label grocery-wizard or label bug).",
            file=sys.stderr,
        )
        return 1

    print(format_work_prompt(entry))
    return 0


def _gh_pr_url_for_current_branch() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "url", "-q", ".url"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    return url or None


def cmd_dev_enhancement_pr_title(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import format_pr_title, get_enhancement

    entry = get_enhancement(args.id)
    if entry is None:
        print(f"Enhancement '{args.id}' not found.", file=sys.stderr)
        return 1
    print(format_pr_title(entry))
    return 0


def cmd_dev_record_manual_verification(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import get_enhancement, record_manual_verification

    entry = get_enhancement(args.id)
    if entry is None:
        print(f"Enhancement '{args.id}' not found.", file=sys.stderr)
        return 1

    pr_url = (args.pr_url or "").strip()
    if not pr_url:
        pr_url = _gh_pr_url_for_current_branch() or ""
    if not pr_url:
        print(
            "Could not resolve PR URL. Pass --pr-url, or open a PR on this branch (gh).",
            file=sys.stderr,
        )
        return 1

    record_manual_verification(
        pr_url=pr_url,
        issue_number=str(args.id).removeprefix("#"),
        note=(args.note or "").strip(),
    )
    print(f"Posted manual verification sign-off on PR: {pr_url}")
    return 0


def cmd_dev_migrate_enhancements_to_github(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_log import migrate_jsonl_to_github

    try:
        created = migrate_jsonl_to_github(dry_run=args.dry_run)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not created:
        print("Nothing to migrate (no legacy JSONL or all IDs already on GitHub).")
        return 0
    if args.dry_run:
        print("Would import:")
    else:
        print("Imported:")
    for row in created:
        eid = row.get("id", "?")
        title = row.get("title", "")
        url = row.get("url", "")
        num = row.get("number")
        suffix = f" → {url}" if url else ""
        num_part = f"#{num} " if num else ""
        print(f"  {num_part}{eid} {title}{suffix}")
    return 0


def cmd_dev_backfill_enhancement_labels(args: argparse.Namespace) -> int:
    from src.grocery_wizard.dev.enhancement_github import GhError, backfill_backlog_labels

    try:
        updated = backfill_backlog_labels(strip_title_prefix=args.strip_title_prefix)
    except GhError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not updated:
        print("No legacy title-matched issues needed updates.")
        return 0
    for row in updated:
        num = row.get("number")
        actions = ", ".join(row.get("actions") or [])
        url = row.get("url") or ""
        suffix = f" ({url})" if url else ""
        print(f"  #{num}: {actions}{suffix}")
    print(f"Updated {len(updated)} issue(s).")
    return 0
