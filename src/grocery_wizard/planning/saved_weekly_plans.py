"""Weekly meal plans stored in Notion."""

from __future__ import annotations

__all__ = [
    "PlanSaveOutcome",
    "SaveWeekChoice",
    "SavedWeeklyPlan",
    "WeeklyPlanSaveResult",
    "canonical_plan_name",
    "ensure_saved_weekly_plan",
    "find_plan_for_week",
    "list_saved_plans",
    "load_plan_recipes",
    "needs_save_week_choice",
    "normalize_recipe_names",
    "plan_recipe_lookup_keys",
    "saved_plan_week_start",
    "week_start_sunday",
]

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Literal

from src.grocery_wizard.integrations.notion import recipe_lookup_key

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe

SaveWeekChoice = Literal["this_week", "next_week"]
PlanSaveOutcome = Literal["created", "updated", "unchanged"]


@dataclass(frozen=True)
class SavedWeeklyPlan:
    """One saved meal plan. ``week_start`` is the Sunday that begins the plan week."""

    week_start: date
    name: str
    recipes: tuple[str, ...]
    page_id: str | None = None


@dataclass(frozen=True)
class WeeklyPlanSaveResult:
    plan: SavedWeeklyPlan
    outcome: PlanSaveOutcome
    previous_recipes: tuple[str, ...]


def week_start_sunday(d: date) -> date:
    """Return the Sunday on or before ``d`` (Sunday-start weeks)."""
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


def needs_save_week_choice(when: date) -> bool:
    """True on Tue/Wed when the user must pick this week vs next week before saving."""
    return when.weekday() in (1, 2)


def saved_plan_week_start(
    when: date,
    *,
    week_choice: SaveWeekChoice | None = None,
) -> date:
    """Return the Sunday week start to use when saving a plan on ``when``."""
    sunday_on_or_before = week_start_sunday(when)
    weekday = when.weekday()
    if weekday in (1, 2):
        if week_choice == "next_week":
            return sunday_on_or_before + timedelta(days=7)
        if week_choice == "this_week":
            return sunday_on_or_before
        raise ValueError("week_choice is required when saving on Tuesday or Wednesday")
    if weekday in (3, 4, 5):
        return sunday_on_or_before + timedelta(days=7)
    return sunday_on_or_before


def canonical_plan_name(week_start: date) -> str:
    return f"{week_start.isoformat()}_plan"


def normalize_recipe_names(recipe_names: list[str]) -> tuple[str, ...]:
    return tuple(name.strip() for name in recipe_names if name.strip())


def plan_recipe_lookup_keys(recipe_names: list[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset(recipe_lookup_key(name) for name in recipe_names)


def list_saved_plans(*, recipes_db: NotionRecipesDB | None = None) -> list[SavedWeeklyPlan]:
    """Return saved plans newest-first, one row per week."""
    from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB

    return NotionWeeklyPlansDB(recipes_db=recipes_db).list_plans()


def load_plan_recipes(
    plan_name: str,
    *,
    recipes_db: NotionRecipesDB | None = None,
) -> list[str]:
    """Return recipe names for a saved plan name, or empty if not found."""
    from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB

    return NotionWeeklyPlansDB(recipes_db=recipes_db).load_plan_recipes(plan_name)


def find_plan_for_week(
    week_start: date,
    *,
    recipes_db: NotionRecipesDB | None = None,
) -> SavedWeeklyPlan | None:
    """Return the saved plan for ``week_start``, if any."""
    from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB

    return NotionWeeklyPlansDB(recipes_db=recipes_db).find_plan_for_week(week_start)


def ensure_saved_weekly_plan(
    recipe_names: list[str],
    *,
    reference_date: date | None = None,
    week_choice: SaveWeekChoice | None = None,
    cached_recipes: list[Recipe] | None = None,
    recipes_db: NotionRecipesDB | None = None,
) -> WeeklyPlanSaveResult:
    """Create or update the single saved plan row for the target week."""
    from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB

    return NotionWeeklyPlansDB(recipes_db=recipes_db).ensure_plan(
        recipe_names,
        reference_date=reference_date,
        week_choice=week_choice,
        cached_recipes=cached_recipes,
    )
