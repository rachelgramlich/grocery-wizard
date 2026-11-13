"""Add a recipe to the in-session weekly plan (Browse grid and shared weekly rules)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.grocery_wizard.config import load_config
from src.grocery_wizard.ui.grocery_helpers import parse_line_items_text
from src.grocery_wizard.ui.views.weekly_plan.state import (
    PLAN_MEAL_COUNT_CONFIRMED_KEY,
    PLAN_MEAL_COUNT_WIDGET_KEY,
    _clear_grocery_result,
    _clear_grocery_session_overrides,
    _invalidate_weekly_plan_save_state,
    _reset_weekly_plan_workflow,
    _set_plan_slot_origins,
    _weekly_plan_mode,
    _write_plan_names,
)


class WeeklyPlanAddOutcome(StrEnum):
    PINNED = "pinned"
    ADDED = "added"
    ALREADY_PINNED = "already_pinned"
    ALREADY_IN_PLAN = "already_in_plan"
    PLAN_FULL = "plan_full"


@dataclass(frozen=True)
class WeeklyPlanAddResult:
    outcome: WeeklyPlanAddOutcome
    message: str
    toast: bool = True


def _meal_count(session_state: Any) -> int:
    default = 1 if _weekly_plan_mode() == "dev" else load_config().default_meals
    return max(1, int(session_state.get("plan_meal_count", default)))


def _current_plan_names(session_state: Any) -> list[str]:
    return parse_line_items_text(session_state.get("plan_meals_text", ""))


def _plan_slot_origins(session_state: Any) -> list[str]:
    return list(session_state.get("plan_slot_origins") or [])


def ensure_weekly_plan_session_for_browse(session_state: Any) -> None:
    """Start a new weekly plan in session when the user has not clicked Continue yet."""
    if _weekly_plan_mode() is not None:
        return
    session_state.weekly_plan_mode = "new"
    _reset_weekly_plan_workflow(clear_mode=False)
    session_state.plan_meals_text = ""
    session_state.plan_meal_count = load_config().default_meals
    session_state.pop(PLAN_MEAL_COUNT_WIDGET_KEY, None)
    session_state.pop(PLAN_MEAL_COUNT_CONFIRMED_KEY, None)


def clamp_prebuild_pinned_recipes(session_state: Any, *, max_pins: int) -> None:
    key = "plan_prebuild_pinned_recipes"
    pinned = list(session_state.get(key) or [])
    if not pinned:
        return
    limit = max(1, int(max_pins))
    if len(pinned) <= limit:
        return
    session_state[key] = pinned[:limit]


def try_pin_recipe(session_state: Any, recipe_name: str, *, max_pins: int) -> WeeklyPlanAddResult:
    pinned = list(session_state.get("plan_prebuild_pinned_recipes") or [])
    if recipe_name in pinned:
        return WeeklyPlanAddResult(
            WeeklyPlanAddOutcome.ALREADY_PINNED,
            "That recipe is already pinned.",
            toast=False,
        )
    if recipe_name in _current_plan_names(session_state):
        return WeeklyPlanAddResult(
            WeeklyPlanAddOutcome.ALREADY_IN_PLAN,
            "Already in your meals.",
            toast=False,
        )
    if len(pinned) >= max(1, int(max_pins)):
        return WeeklyPlanAddResult(
            WeeklyPlanAddOutcome.PLAN_FULL,
            f"You can pin at most {max_pins} meals for this week.",
            toast=False,
        )
    pinned.append(recipe_name)
    session_state.plan_prebuild_pinned_recipes = pinned
    return WeeklyPlanAddResult(
        WeeklyPlanAddOutcome.PINNED,
        f"Pinned {recipe_name} for this week.",
    )


def try_append_to_built_plan(
    session_state: Any,
    recipe_name: str,
    *,
    meal_count: int,
) -> WeeklyPlanAddResult:
    current = _current_plan_names(session_state)
    if recipe_name in current:
        return WeeklyPlanAddResult(
            WeeklyPlanAddOutcome.ALREADY_IN_PLAN,
            "Already in your meals.",
            toast=False,
        )
    if len(current) >= max(1, int(meal_count)):
        return WeeklyPlanAddResult(
            WeeklyPlanAddOutcome.PLAN_FULL,
            "Your meal plan is full. Open Create weekly plan to swap a meal.",
            toast=False,
        )
    updated = [*current, recipe_name]
    origins = _plan_slot_origins(session_state)
    while len(origins) < len(updated):
        origins.append("suggested")
    origins[len(current)] = "manual"
    _write_plan_names(updated)
    _set_plan_slot_origins(origins[: len(updated)])
    _invalidate_weekly_plan_save_state()
    _clear_grocery_session_overrides()
    _clear_grocery_result()
    return WeeklyPlanAddResult(
        WeeklyPlanAddOutcome.ADDED,
        f"Added {recipe_name} to this week.",
    )


def add_recipe_to_week_from_browse(session_state: Any, recipe_name: str) -> WeeklyPlanAddResult:
    """Pin or append a recipe using the same rules as the weekly plan builder."""
    ensure_weekly_plan_session_for_browse(session_state)
    meal_count = _meal_count(session_state)
    current = _current_plan_names(session_state)
    if not current:
        clamp_prebuild_pinned_recipes(session_state, max_pins=meal_count)
        return try_pin_recipe(session_state, recipe_name, max_pins=meal_count)
    return try_append_to_built_plan(session_state, recipe_name, meal_count=meal_count)
