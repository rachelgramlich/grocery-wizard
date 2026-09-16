"""Production workflow CLI commands (recipes, planning, grocery list, pantry)."""

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

    plan_parser = subparsers.add_parser(
        "plan-recipes",
        help="Pick dinners for the week (saves week_plan.json)",
    )
    plan_parser.add_argument(
        "--meals",
        type=int,
        default=None,
        help="How many dinners to plan (default: from your config, usually 7)",
    )
    plan_parser.set_defaults(func=cmd_plan)

    grocery_parser = subparsers.add_parser(
        "create-grocery-list",
        help="Build your shopping list from this week's plan",
    )
    grocery_parser.add_argument(
        "--recipes",
        help="Use these recipe names instead of the saved week plan",
    )
    grocery_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output: hide excluded staples and skip the re-add prompt",
    )
    grocery_parser.add_argument(
        "--backfill-missing",
        action="store_true",
        help=("Scrape Notion recipes that have a link but no ingredients, then build the list"),
    )
    grocery_parser.add_argument(
        "--include-staples",
        action="store_true",
        help="Don't exclude pantry staples (salt, oil, etc.) from the list",
    )
    grocery_parser.add_argument(
        "--no-recurring-weekly-items",
        action="store_true",
        help="Omit recurring weekly items (berries, milk, etc.) from the list",
    )
    grocery_parser.set_defaults(func=cmd_grocery)

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


def cmd_plan(args: argparse.Namespace) -> int:
    from src.grocery_wizard.planning.meal_planner import run_meal_planner

    config = load_config()
    db = NotionRecipesDB(config)
    meals = args.meals or config.default_meals
    plan = run_meal_planner(db, meals=meals)
    return 0 if plan else 1


def cmd_grocery(args: argparse.Namespace) -> int:
    from src.grocery_wizard.shopping.grocery_list import run_grocery_list

    config = load_config()
    db = NotionRecipesDB(config)

    recipe_names: list[str] | None = None
    if args.recipes:
        recipe_names = [name.strip() for name in args.recipes.split(",") if name.strip()]

    return run_grocery_list(
        db,
        recipe_names=recipe_names,
        quiet=args.quiet,
        backfill_missing=args.backfill_missing,
        exclude_pantry=not args.include_staples,
        include_recurring_weekly_items=not args.no_recurring_weekly_items,
    )


def cmd_pantry(_args: argparse.Namespace) -> int:
    from src.grocery_wizard.shopping.pantry import run_pantry_interactive

    return run_pantry_interactive()
