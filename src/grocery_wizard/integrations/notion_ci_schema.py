"""Verify Notion CI test databases: reachability, schema, recipe query smoke (#426)."""

from __future__ import annotations

__all__ = [
    "NotionCiCheckReport",
    "collect_pantry_schema_errors",
    "collect_recipes_schema_errors",
    "collect_recurring_schema_errors",
    "collect_weekly_plans_schema_errors",
    "format_notion_ci_report",
    "run_notion_ci_checks",
    "verify_recipe_query_smoke",
]

from dataclasses import dataclass, field

from src.grocery_wizard.config import Config, load_config
from src.grocery_wizard.integrations.notion import DatabaseSchema, NotionRecipesDB, Recipe
from src.grocery_wizard.integrations.notion_household import (
    PANTRY_NAME_COLUMN,
    PLAN_NAME_COLUMN,
    PLAN_RECIPES_COLUMN,
    PLAN_WEEK_START_COLUMN,
    RECURRING_NAME_COLUMN,
    resolve_pantry_aisle_column,
)
from src.grocery_wizard.integrations.notion_table import NotionDatabase

CI_RECIPES_LABEL = "[GW CI] Recipes"
CI_PANTRY_LABEL = "[GW CI] Pantry Staples"
CI_RECURRING_LABEL = "[GW CI] Recurring Weekly Items"
CI_WEEKLY_PLANS_LABEL = "[GW CI] Weekly Meal Plans"


@dataclass
class NotionCiCheckReport:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _column_type_errors(
    *,
    database_label: str,
    column_types: dict[str, str],
    name: str,
    expected_types: tuple[str, ...],
) -> list[str]:
    if name not in column_types:
        found = ", ".join(sorted(column_types)) or "(none)"
        return [
            (
                f"{database_label}: missing property {name!r} (found: {found}). "
                "Rename or restore the column to match production."
            )
        ]
    actual = column_types[name]
    if actual not in expected_types:
        expected = ", ".join(expected_types)
        return [f"{database_label}: property {name!r} has type {actual!r}; expected {expected}."]
    return []


def collect_recipes_schema_errors(
    schema: DatabaseSchema,
    *,
    database_label: str = CI_RECIPES_LABEL,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _column_type_errors(
            database_label=database_label,
            column_types={n: c.type for n, c in schema.all_columns.items()},
            name=schema.name_column,
            expected_types=("title",),
        )
    )
    errors.extend(
        _column_type_errors(
            database_label=database_label,
            column_types={n: c.type for n, c in schema.all_columns.items()},
            name=schema.link_column,
            expected_types=("url",),
        )
    )
    if not schema.ingredients_column:
        errors.append(
            f"{database_label}: missing Ingredients text column. "
            "Add Ingredients (rich_text) or set GROCERY_WIZARD_INGREDIENTS_COLUMN."
        )
    elif schema.ingredients_column:
        errors.extend(
            _column_type_errors(
                database_label=database_label,
                column_types={n: c.type for n, c in schema.all_columns.items()},
                name=schema.ingredients_column,
                expected_types=("rich_text", "text"),
            )
        )
    return errors


def collect_pantry_schema_errors(
    column_types: dict[str, str],
    *,
    database_label: str = CI_PANTRY_LABEL,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _column_type_errors(
            database_label=database_label,
            column_types=column_types,
            name=PANTRY_NAME_COLUMN,
            expected_types=("title",),
        )
    )
    try:
        aisle_column = resolve_pantry_aisle_column(column_types)
    except ValueError as exc:
        errors.append(f"{database_label}: {exc}")
    else:
        errors.extend(
            _column_type_errors(
                database_label=database_label,
                column_types=column_types,
                name=aisle_column,
                expected_types=("select",),
            )
        )
    return errors


def collect_recurring_schema_errors(
    column_types: dict[str, str],
    *,
    database_label: str = CI_RECURRING_LABEL,
) -> list[str]:
    return _column_type_errors(
        database_label=database_label,
        column_types=column_types,
        name=RECURRING_NAME_COLUMN,
        expected_types=("title",),
    )


def collect_weekly_plans_schema_errors(
    column_types: dict[str, str],
    *,
    database_label: str = CI_WEEKLY_PLANS_LABEL,
) -> list[str]:
    errors: list[str] = []
    for name, expected in (
        (PLAN_NAME_COLUMN, ("title",)),
        (PLAN_WEEK_START_COLUMN, ("date",)),
        (PLAN_RECIPES_COLUMN, ("relation",)),
    ):
        errors.extend(
            _column_type_errors(
                database_label=database_label,
                column_types=column_types,
                name=name,
                expected_types=expected,
            )
        )
    return errors


def _open_household_database(
    config: Config,
    database_id: str | None,
    *,
    database_label: str,
    report: NotionCiCheckReport,
) -> NotionDatabase | None:
    if not database_id:
        report.errors.append(f"{database_label}: database ID is not set in config.")
        return None
    try:
        return NotionDatabase(config, database_id)
    except Exception as exc:
        report.errors.append(f"{database_label}: cannot reach database ({database_id}): {exc}")
        return None


def _verify_recipes_database(
    config: Config,
    report: NotionCiCheckReport,
) -> NotionRecipesDB | None:
    db_id = config.notion_recipe_database_id
    if not db_id:
        report.errors.append(f"{CI_RECIPES_LABEL}: NOTION_RECIPE_DATABASE_ID is not set.")
        return None
    try:
        recipes_db = NotionRecipesDB(config)
    except Exception as exc:
        report.errors.append(f"{CI_RECIPES_LABEL}: cannot reach database ({db_id}): {exc}")
        return None
    report.errors.extend(collect_recipes_schema_errors(recipes_db.schema))
    return recipes_db


def verify_recipe_query_smoke(
    recipes_db: NotionRecipesDB | None,
    report: NotionCiCheckReport,
    *,
    database_label: str = CI_RECIPES_LABEL,
) -> None:
    if recipes_db is None:
        return
    try:
        recipes: list[Recipe] = recipes_db.query_recipes()
    except Exception as exc:
        report.errors.append(f"{database_label}: query_recipes failed: {exc}")
        return
    if not recipes:
        report.notes.append(
            f"{database_label}: database is empty; recipe query smoke skipped "
            "(seed CI recipes for stronger checks)."
        )
        return
    parseable = [recipe for recipe in recipes if recipe.name.strip()]
    if not parseable:
        report.errors.append(
            f"{database_label}: {len(recipes)} page(s) returned but none had a readable name."
        )


def run_notion_ci_checks(config: Config | None = None) -> NotionCiCheckReport:
    """Live Notion: verify CI databases and run a minimal recipe query smoke."""
    cfg = config or load_config()
    report = NotionCiCheckReport()

    recipes_db = _verify_recipes_database(cfg, report)

    pantry_db = _open_household_database(
        cfg,
        cfg.notion_pantry_database_id,
        database_label=CI_PANTRY_LABEL,
        report=report,
    )
    if pantry_db is not None:
        report.errors.extend(collect_pantry_schema_errors(pantry_db.column_types))

    recurring_db = _open_household_database(
        cfg,
        cfg.notion_recurring_weekly_database_id,
        database_label=CI_RECURRING_LABEL,
        report=report,
    )
    if recurring_db is not None:
        report.errors.extend(collect_recurring_schema_errors(recurring_db.column_types))

    plans_db = _open_household_database(
        cfg,
        cfg.notion_weekly_meal_plans_database_id,
        database_label=CI_WEEKLY_PLANS_LABEL,
        report=report,
    )
    if plans_db is not None:
        report.errors.extend(collect_weekly_plans_schema_errors(plans_db.column_types))

    verify_recipe_query_smoke(recipes_db, report)
    return report


def format_notion_ci_report(report: NotionCiCheckReport) -> str:
    lines: list[str] = []
    if report.ok:
        lines.append("Notion CI checks passed.")
    else:
        lines.extend(["Notion CI checks FAILED:", *[f"  - {error}" for error in report.errors]])
    lines.extend(f"  note: {note}" for note in report.notes)
    return "\n".join(lines)


def main() -> int:
    report = run_notion_ci_checks()
    print(format_notion_ci_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
