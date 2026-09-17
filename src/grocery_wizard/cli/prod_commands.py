"""Production workflow CLI commands (recipes, pantry)."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from src.grocery_wizard.config import load_config
from src.grocery_wizard.integrations.notion import NotionRecipesDB

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register_prod_commands(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    add_parser = subparsers.add_parser(
        "add-recipe",
        help="Save a new recipe from a URL into Notion",
    )
    add_parser.add_argument(
        "urls",
        nargs="*",
        help="Recipe page URLs to save (or paste URLs when prompted)",
    )
    add_parser.set_defaults(func=cmd_add)

    pantry_parser = subparsers.add_parser(
        "edit-pantry",
        help="Edit what's always in your kitchen (won't appear on shopping list)",
    )
    pantry_parser.set_defaults(func=cmd_pantry)


def cmd_add(args: argparse.Namespace) -> int:
    from src.grocery_wizard.recipes.add_recipe import add_recipes_from_urls, read_urls_from_stdin

    config = load_config()
    db = NotionRecipesDB(config)

    urls = list(args.urls)
    if not urls:
        urls = read_urls_from_stdin()
    if not urls:
        print("No URLs provided.", file=sys.stderr)
        return 1

    created = add_recipes_from_urls(db, urls)
    print(f"\nCreated {len(created)} recipe(s).")
    return 0


def cmd_pantry(_args: argparse.Namespace) -> int:
    print("Command 'edit-pantry' was removed.", file=sys.stderr)
    print(
        "Use the Streamlit app (`just grocery-ui`) — **Pantry & recurring** tab.",
        file=sys.stderr,
    )
    return 1
