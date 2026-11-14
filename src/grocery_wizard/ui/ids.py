"""Stable UI identifiers (page / block / control). See docs/ui/ui-map.md."""

from __future__ import annotations

from typing import Final

# --- Pages (segment slugs) ---

PAGE_SLUG_GLOBAL: Final = "global"
PAGE_SLUG_WEEKLY: Final = "weekly"
PAGE_SLUG_ADD: Final = "add"
PAGE_SLUG_PANTRY: Final = "pantry"
PAGE_SLUG_MAINTENANCE: Final = "maintenance"
PAGE_SLUG_BROWSE: Final = "browse"

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
BLOCK_WEEKLY_MEALS_SAVE: Final = "weekly.meals.save"
BLOCK_WEEKLY_GROCERY_PRE_BUILD: Final = "weekly.grocery_pre_build"
BLOCK_WEEKLY_GROCERY_RECIPE_REVIEW: Final = "weekly.grocery_recipe_review"
BLOCK_WEEKLY_GROCERY_RESULT: Final = "weekly.grocery_result"
BLOCK_WEEKLY_GROCERY_RESULT_SUMMARY: Final = "weekly.grocery_result.summary"
BLOCK_WEEKLY_GROCERY_RESULT_CUSTOMIZE: Final = "weekly.grocery_result.customize"
CONTROL_WEEKLY_GROCERY_RESULT_VIEW_DEBUG_LOG_NOTION: Final = (
    "weekly.grocery_result.view_debug_log_notion"
)
CONTROL_WEEKLY_GROCERY_RESULT_DOWNLOAD_DEBUG_LOG: Final = "weekly.grocery_result.download_debug_log"

# --- Add blocks ---

BLOCK_ADD_URL: Final = "add.url"
BLOCK_ADD_MANUAL: Final = "add.manual"
BLOCK_ADD_NYT: Final = "add.nyt"

# --- Pantry blocks ---

BLOCK_PANTRY_RECURRING: Final = "pantry.recurring"
BLOCK_PANTRY_STAPLES: Final = "pantry.staples"

# --- Browse blocks ---

BLOCK_BROWSE_FILTERS: Final = "browse.filters"
BLOCK_BROWSE_GRID: Final = "browse.grid"
CONTROL_BROWSE_APPLY: Final = "browse.apply"
CONTROL_BROWSE_RESET: Final = "browse.reset"
CONTROL_BROWSE_LOAD_MORE: Final = "browse.load_more"
CONTROL_BROWSE_FILTERS_HAS_IMAGE: Final = "browse.filters.has_image"
CONTROL_BROWSE_FILTERS_INCLUDE_PAUSED: Final = "browse.filters.include_paused"
CONTROL_BROWSE_FILTERS_INCLUDE_DEPRECATED: Final = "browse.filters.include_deprecated"
CONTROL_BROWSE_CARD_ADD: Final = "browse.card.add"

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
