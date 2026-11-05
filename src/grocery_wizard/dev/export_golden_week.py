"""Export a saved meal plan from Notion into a golden grocery week JSON fixture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.grocery_wizard.config import load_config
from src.grocery_wizard.integrations.notion import NotionRecipesDB, recipe_lookup_key
from src.grocery_wizard.planning.saved_weekly_plans import list_saved_plans
from src.grocery_wizard.shopping.pantry import load_pantry
from src.grocery_wizard.shopping.recurring_weekly_items import load_recurring_weekly_items
from src.grocery_wizard.shopping.weekly_grocery_export import export_grocery_lines_for_meal_plan


def _repo_golden_weeks_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "golden_grocery_weeks"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--id",
        required=True,
        help="Fixture filename stem (writes tests/fixtures/golden_grocery_weeks/<id>.json)",
    )
    parser.add_argument(
        "recipes",
        nargs="*",
        help="Planned recipe names (same strings as in your weekly plan)",
    )
    parser.add_argument(
        "--from-saved-plan",
        metavar="PLAN_NAME",
        help="Load recipe names from a Notion saved plan (e.g. 2026-11-01_plan)",
    )
    parser.add_argument(
        "--description",
        default="Exported from Notion via export-golden-week",
    )
    parser.add_argument(
        "--extra-items",
        default="",
        help="Extra items text area content (optional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON to stdout instead of writing a file",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    db = NotionRecipesDB(cfg)
    recipe_names: list[str]
    source_plan_name: str | None = None
    if args.from_saved_plan:
        if args.recipes:
            raise SystemExit("Use either --from-saved-plan or explicit recipe names, not both.")
        all_recipes = db.query_recipes()
        names_by_page = {r.page_id: r.name for r in all_recipes}
        plans = list_saved_plans(recipes_db=db, recipe_names_by_page_id=names_by_page)
        match = next((p for p in plans if p.name == args.from_saved_plan), None)
        if match is None:
            raise SystemExit(f"No saved plan named {args.from_saved_plan!r}")
        recipe_names = list(match.recipes)
        source_plan_name = match.name
        default_desc = "Exported from Notion via export-golden-week"
        if not args.description or args.description == default_desc:
            args.description = (
                f"Exported from Notion saved plan {match.name} (week of {match.week_start})."
            )
    else:
        if not args.recipes:
            raise SystemExit("Provide recipe names or --from-saved-plan.")
        recipe_names = list(args.recipes)

    pantry = load_pantry()
    recurring = load_recurring_weekly_items()
    expect_lines = export_grocery_lines_for_meal_plan(
        db,
        recipe_names,
        pantry_names=pantry,
        recurring=recurring,
        extra_items=args.extra_items,
    )

    recipes_by_key = {recipe_lookup_key(r.name): r for r in db.query_recipes()}
    rows = []
    for name in recipe_names:
        recipe = recipes_by_key.get(recipe_lookup_key(name))
        if recipe is None:
            raise SystemExit(f"Recipe not found in Notion: {name!r}")
        rows.append(
            {
                "name": recipe.name,
                "link": recipe.link,
                "ingredients": recipe.ingredients or "",
            }
        )

    week = {
        "id": args.id,
        "description": args.description,
        "pantry": sorted(pantry),
        "recurring": recurring,
        "extra_items": args.extra_items,
        "recipes": rows,
        "expect_grocery_lines": expect_lines,
    }
    if source_plan_name:
        week["source_plan_name"] = source_plan_name

    payload = json.dumps(week, indent=2, ensure_ascii=False) + "\n"
    if args.dry_run:
        sys.stdout.write(payload)
        return 0

    out_dir = _repo_golden_weeks_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.id}.json"
    out.write_text(payload, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
