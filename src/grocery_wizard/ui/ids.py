"""Stable UI identifiers (page / block / control). See docs/ui-map.md."""

from __future__ import annotations

from typing import Final

# --- Pages (segment slugs) ---

PAGE_SLUG_GLOBAL: Final = "global"
PAGE_SLUG_WEEKLY: Final = "weekly"
PAGE_SLUG_ADD: Final = "add"
PAGE_SLUG_PANTRY: Final = "pantry"
PAGE_SLUG_MAINTENANCE: Final = "maintenance"

# --- Global controls (page `global`, block `global`) ---

CONTROL_GLOBAL_PAGE_PICKER: Final = "global.global.page_picker"
CONTROL_GLOBAL_REFRESH: Final = "global.global.refresh"
CONTROL_GLOBAL_FEEDBACK: Final = "global.global.feedback"
CONTROL_GLOBAL_LOADING: Final = "global.global.loading"

# --- Weekly blocks (ordered where noted) ---

BLOCK_WEEKLY_PLAN_START: Final = "weekly.plan_start"
BLOCK_WEEKLY_MEALS: Final = "weekly.meals"
BLOCK_WEEKLY_MEALS_BUILD: Final = "weekly.meals.build"
BLOCK_WEEKLY_MEALS_LIST: Final = "weekly.meals.list"
BLOCK_WEEKLY_GROCERY_PRE_BUILD: Final = "weekly.grocery_pre_build"
BLOCK_WEEKLY_GROCERY_RECIPE_REVIEW: Final = "weekly.grocery_recipe_review"
BLOCK_WEEKLY_GROCERY_RESULT: Final = "weekly.grocery_result"
BLOCK_WEEKLY_GROCERY_RESULT_SUMMARY: Final = "weekly.grocery_result.summary"
BLOCK_WEEKLY_GROCERY_RESULT_CUSTOMIZE: Final = "weekly.grocery_result.customize"

# --- Add blocks ---

BLOCK_ADD_URL: Final = "add.url"
BLOCK_ADD_MANUAL: Final = "add.manual"
BLOCK_ADD_NYT: Final = "add.nyt"

# --- Pantry blocks ---

BLOCK_PANTRY_RECURRING: Final = "pantry.recurring"
BLOCK_PANTRY_STAPLES: Final = "pantry.staples"

# --- Maintenance blocks ---

BLOCK_MAINTENANCE_MEAL_PLAN_STATUS: Final = "maintenance.meal_plan_status"
BLOCK_MAINTENANCE_BACKFILL_AUTO: Final = "maintenance.backfill_auto"
BLOCK_MAINTENANCE_BACKFILL_MANUAL: Final = "maintenance.backfill_manual"

# Dev jump targets → weekly block IDs
DEV_JUMP_BLOCK_ID: Final = {
    "meals_filled": BLOCK_WEEKLY_MEALS,
    "pre_build_grocery": BLOCK_WEEKLY_GROCERY_PRE_BUILD,
    "per_recipe_review": BLOCK_WEEKLY_GROCERY_RECIPE_REVIEW,
    "grocery_result": BLOCK_WEEKLY_GROCERY_RESULT,
}


def control_streamlit_key(control_id: str) -> str:
    """Map a control FQN to a Streamlit widget ``key`` (dots → underscores)."""
    return control_id.replace(".", "_")
