"""NYT Cooking integration CLI commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from src.grocery_wizard.config import load_config
from src.grocery_wizard.integrations.notion import NotionRecipesDB

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register_nyt_commands(nyt_subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    nyt_auth_status_parser = nyt_subparsers.add_parser(
        "auth-status",
        help="Check whether NYT Cooking credentials are configured (env vars)",
    )
    nyt_auth_status_parser.set_defaults(func=cmd_nyt_auth_status)

    nyt_saved_parser = nyt_subparsers.add_parser(
        "saved",
        help="List saved recipe box recipes",
    )
    nyt_saved_parser.add_argument(
        "--collection",
        help="Filter to a specific NYT recipe-box folder by name",
    )
    nyt_saved_parser.set_defaults(func=cmd_nyt_saved)

    nyt_sync_parser = nyt_subparsers.add_parser(
        "sync",
        help="Sync NYT saved recipes to Notion (skips duplicates)",
    )
    nyt_sync_parser.add_argument(
        "--collection",
        help="Sync only recipes from a specific NYT folder (skips interactive picker)",
    )
    nyt_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview recipes that would be added without writing to Notion",
    )
    nyt_sync_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Review and confirm each recipe before creating (default: batch import)",
    )
    nyt_sync_parser.set_defaults(func=cmd_nyt_sync)

    nyt_review_parser = nyt_subparsers.add_parser(
        "review-metadata",
        help="Show metadata assigned during the last NYT sync",
    )
    nyt_review_parser.set_defaults(func=cmd_nyt_review_metadata)

    nyt_apply_parser = nyt_subparsers.add_parser(
        "apply-metadata",
        help="Apply metadata corrections from a JSON file",
    )
    nyt_apply_parser.add_argument(
        "corrections_file",
        help='JSON file: [{"page_id": "...", "fields": {"Meal": "Dessert"}}]',
    )
    nyt_apply_parser.set_defaults(func=cmd_nyt_apply_metadata)

    nyt_reclassify_parser = nyt_subparsers.add_parser(
        "reclassify",
        help="Re-run Meal and Weeknight Friendly for NYT-synced recipes",
    )
    nyt_reclassify_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to Notion",
    )
    nyt_reclassify_parser.set_defaults(func=cmd_nyt_reclassify)


def cmd_nyt_auth_status(_args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import (
        NytAuthError,
        NYTCookingClient,
        credentials_status,
    )

    status = credentials_status()
    if not status["configured"]:
        print("NYT Cooking credentials: not configured")
        print("Set NYT_S_COOKIE and NYT_REGI_ID (or NYT_USER_ID) in your environment.")
        print("See README for how to copy values from browser DevTools.")
        return 1

    print("NYT Cooking credentials: configured (environment)")
    print(f"regi_id: {status['regi_id']}")

    client = NYTCookingClient()
    try:
        client.verify_auth()
    except NytAuthError as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1

    print("Verification: OK")
    return 0


def cmd_nyt_saved(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import NytAuthError, NYTCookingClient

    client = NYTCookingClient()
    collection_id: str | None = None

    if args.collection:
        collection = client.find_collection_by_name(args.collection)
        if collection is None:
            print(
                f"Collection '{args.collection}' not found; listing full recipe box.",
                file=sys.stderr,
            )
        else:
            collection_id = collection.id
            print(f"Folder: {collection.name} ({collection.recipe_count} recipes)")

    try:
        recipes = list(client.iter_all_saved_recipes(collection_id=collection_id))
    except NytAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not recipes:
        print("No saved recipes found.")
        return 0

    for index, recipe in enumerate(recipes, start=1):
        author = f" — {recipe.author}" if recipe.author else ""
        print(f"{index:4d}. {recipe.name}{author}")
        print(f"      {recipe.url}")
    print(f"\nTotal: {len(recipes)} recipe(s)")
    return 0


def cmd_nyt_sync(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import (
        NytAuthError,
        NYTCookingClient,
        NytSyncCancelledError,
        format_metadata_review,
        prompt_collection_choice,
        save_sync_report,
        sync_saved_recipes_to_notion,
    )

    config = load_config()
    db = NotionRecipesDB(config)
    client = NYTCookingClient()

    if args.dry_run:
        print("Dry run — no recipes will be written to Notion.\n")

    collection_id: str | None = None
    collection_label: str | None = None

    try:
        if args.collection:
            pass
        else:
            collection_id, collection_label = prompt_collection_choice(client, on_info=print)
            print()
    except NytAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except NytSyncCancelledError as exc:
        print(str(exc))
        return 0

    try:
        summary = sync_saved_recipes_to_notion(
            db,
            client,
            collection_name=args.collection,
            collection_id=collection_id,
            collection_label=collection_label,
            dry_run=args.dry_run,
            no_confirm=not args.confirm,
            on_progress=print,
        )
    except NytAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.dry_run and summary.created_recipes:
        save_sync_report(summary)

    print()
    print(
        f"Sync complete: {summary.total} in NYT, "
        f"{summary.skipped_existing} already in Notion, "
        f"{summary.created} created, "
        f"{summary.dry_run} would add, "
        f"{summary.failed} failed."
    )

    if summary.created_recipes:
        print()
        report = {
            "synced_at": "",
            "collection": summary.collection_label,
            "created": [
                {
                    "page_id": r.page_id,
                    "name": r.name,
                    "url": r.url,
                    "metadata": r.metadata,
                    "flags": r.flags,
                }
                for r in summary.created_recipes
            ],
        }
        print(format_metadata_review(report))
        if not args.dry_run and summary.created:
            print("Ask your agent to review flagged recipes, or run: nyt review-metadata")
    return 0


def cmd_nyt_review_metadata(_args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import (
        format_metadata_review,
        load_sync_report,
    )

    report = load_sync_report()
    if report is None:
        print("No NYT sync report found. Run `nyt sync` first.")
        return 1
    print(format_metadata_review(report))
    return 0


def cmd_nyt_apply_metadata(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import apply_metadata_corrections

    path = Path(args.corrections_file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    corrections = json.loads(path.read_text())
    if not isinstance(corrections, list):
        print("Corrections file must be a JSON array.", file=sys.stderr)
        return 1

    config = load_config()
    db = NotionRecipesDB(config)
    updated = apply_metadata_corrections(db, corrections)
    print(f"Updated {updated} recipe(s).")
    return 0


def cmd_nyt_reclassify(args: argparse.Namespace) -> int:
    from src.grocery_wizard.integrations.nyt_cooking import (
        NYTCookingClient,
        format_reclassify_summary,
        reclassify_nyt_synced_recipes,
    )

    config = load_config()
    db = NotionRecipesDB(config)
    client = NYTCookingClient()

    if args.dry_run:
        print("Dry run — no recipes will be written to Notion.\n")

    summary = reclassify_nyt_synced_recipes(
        db,
        client,
        dry_run=args.dry_run,
        on_progress=print,
    )
    print()
    print(format_reclassify_summary(summary))
    return 0
