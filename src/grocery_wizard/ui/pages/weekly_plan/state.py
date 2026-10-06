"""Shared session state helpers for the weekly plan / grocery wizard."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import streamlit as st

from src.grocery_wizard.config import WEEK_PLAN_PATH
from src.grocery_wizard.integrations.notion import recipe_lookup_key
from src.grocery_wizard.planning.meal_planner import save_week_plan
from src.grocery_wizard.planning.saved_weekly_plans import (
    SavedWeeklyPlan,
    SaveWeekChoice,
    WeeklyPlanSaveResult,
    ensure_saved_weekly_plan,
    find_plan_for_week,
    needs_save_week_choice,
    normalize_recipe_names,
    saved_plan_week_start,
)
from src.grocery_wizard.recipes.recipe_meal_plan_stats import sync_plan_selection_stats
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.grocery_flow import (
    GROCERY_STASH_NOTION_GENERATION_KEY,
    bump_grocery_pre_extra_items_widget,
    grocery_pre_extra_items_widget_key,
    recipe_review_plan_fingerprint,
)
from src.grocery_wizard.ui.grocery_flow import (
    clear_grocery_session_overrides as _clear_grocery_session_overrides_state,
)
from src.grocery_wizard.ui.grocery_flow import (
    effective_recurring_items as _effective_recurring_items_state,
)
from src.grocery_wizard.ui.grocery_flow import (
    session_pantry_extra as _session_pantry_extra_state,
)
from src.grocery_wizard.ui.grocery_helpers import parse_line_items_text
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.notion_cache import (
    invalidate_notion_cache,
    invalidate_saved_plans_cache,
    notion_cache_generation,
)

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import Recipe

_WEEKLY_PLAN_MODES = ("new", "saved", "dev")
_SAVE_WEEK_CHOICE_KEY = "weekly_plan_save_week_choice"
# Widget key for meal count; ``plan_meal_count`` persists when the weekly tab is not rendered.
PLAN_MEAL_COUNT_WIDGET_KEY = "plan_meal_count_input"
PLAN_FORCE_OPEN_1A_KEY = "plan_force_open_1a"
_OVERWRITE_CONFIRM_FP_KEY = "weekly_plan_overwrite_confirm_fingerprint"
_RUN_GROCERY_AFTER_OVERWRITE_KEY = "weekly_plan_run_grocery_after_overwrite"


def _current_plan_names() -> list[str]:
    return parse_line_items_text(st.session_state.get("plan_meals_text", ""))


def _write_plan_names(names: list[str]) -> None:
    st.session_state.plan_meals_text = "\n".join(names)


def _plan_slot_origins() -> list[str]:
    return list(st.session_state.get("plan_slot_origins") or [])


def _set_plan_slot_origins(origins: list[str]) -> None:
    st.session_state.plan_slot_origins = list(origins)


def _session_pantry_extra() -> set[str]:
    return _session_pantry_extra_state(st.session_state)


def _grocery_pre_extra_items_widget_key() -> str:
    return grocery_pre_extra_items_widget_key(st.session_state)


def _bump_grocery_pre_extra_items_widget() -> None:
    bump_grocery_pre_extra_items_widget(st.session_state)


def _clear_grocery_session_overrides() -> None:
    _clear_grocery_session_overrides_state(st.session_state)


def _clear_grocery_pre_extra_items() -> None:
    _bump_grocery_pre_extra_items_widget()


def _effective_recurring_items(template: list[str]) -> list[str]:
    return _effective_recurring_items_state(st.session_state, template)


def _render_persistence_scope_radio(*, key: str) -> str:
    """Return ``session`` or ``template`` for pantry / recurring edits."""
    return st.radio(
        "Apply change to",
        options=["session", "template"],
        format_func=lambda choice: (
            "This run only (this week's grocery list)"
            if choice == "session"
            else "Recurring template (saved for future weeks)"
        ),
        horizontal=False,
        key=key,
    )


def _clear_grocery_result(*, clear_pre_extra_items: bool = True) -> None:
    """Remove the cached grocery result, review state, and associated widget state."""
    for key in (
        "grocery_result",
        "grocery_readd",
        "grocery_remove_once",
        "grocery_final_list",
        "grocery_final_list_fingerprint",
        "meals_final_list",
        "meals_final_list_fingerprint",
        "grocery_per_recipe_review",
        "grocery_review_baseline",
        "grocery_review_options",
        "grocery_review_recipes",
        "grocery_review_plan_fingerprint",
        "grocery_review_baseline",
        "grocery_review_save_to_notion",
        GROCERY_STASH_NOTION_GENERATION_KEY,
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("review_ing_"):
            st.session_state.pop(key, None)
    if clear_pre_extra_items:
        _clear_grocery_pre_extra_items()


def _reset_weekly_plan_workflow(*, clear_mode: bool = False) -> None:
    """Clear meal-plan and grocery state for a fresh weekly-plan session."""
    for key in (
        "plan_meals_text",
        "plan_rejected_names",
        "plan_slot_origins",
        "weekly_plan_loaded_name",
        "weekly_plan_last_saved_name",
        "weekly_plan_saved_fingerprint",
        "plan_prebuild_pinned_recipes",
        "plan_last_week_filters",
    ):
        st.session_state.pop(key, None)
    if clear_mode:
        st.session_state.pop("weekly_plan_mode", None)
        st.session_state.pop("plan_meal_count", None)
        st.session_state.pop(PLAN_MEAL_COUNT_WIDGET_KEY, None)
    _clear_grocery_result()


def _weekly_plan_mode_choices() -> tuple[str, ...]:
    return _WEEKLY_PLAN_MODES


def _weekly_plan_mode() -> str | None:
    mode = st.session_state.get("weekly_plan_mode")
    if mode not in _WEEKLY_PLAN_MODES:
        return None
    return mode


def _weekly_plan_reference_date() -> date:
    return datetime.now(tz=UTC).date()


def _save_week_choice() -> SaveWeekChoice | None:
    when = _weekly_plan_reference_date()
    if not needs_save_week_choice(when):
        return None
    choice = st.session_state.get(_SAVE_WEEK_CHOICE_KEY)
    if choice in ("this_week", "next_week"):
        return choice
    return "this_week"


def _resolve_save_week_start() -> date:
    when = _weekly_plan_reference_date()
    return saved_plan_week_start(when, week_choice=_save_week_choice())


def _render_save_week_choice_buttons() -> None:
    """Tue/Wed: pick target week with buttons (avoids duplicate widget keys)."""
    when = _weekly_plan_reference_date()
    if not needs_save_week_choice(when):
        return
    if _SAVE_WEEK_CHOICE_KEY not in st.session_state:
        st.session_state[_SAVE_WEEK_CHOICE_KEY] = "this_week"
    choice = _save_week_choice()
    st.markdown("**Save this plan to**")
    col_this, col_next = st.columns(2)
    with col_this:
        if st.button(
            "This week",
            key="weekly_plan_pick_this_week",
            type="primary" if choice == "this_week" else "secondary",
            use_container_width=True,
        ):
            st.session_state[_SAVE_WEEK_CHOICE_KEY] = "this_week"
    with col_next:
        if st.button(
            "Next week",
            key="weekly_plan_pick_next_week",
            type="primary" if choice == "next_week" else "secondary",
            use_container_width=True,
        ):
            st.session_state[_SAVE_WEEK_CHOICE_KEY] = "next_week"


def _weekly_plan_fingerprint(recipe_names: list[str], week_start: date) -> tuple[str, ...]:
    return (week_start.isoformat(), *normalize_recipe_names(recipe_names))


def _matching_saved_plan(recipe_names: list[str]) -> SavedWeeklyPlan | None:
    week_start = _resolve_save_week_start()
    recipes = normalize_recipe_names(recipe_names)
    if not recipes:
        return None

    fingerprint = _weekly_plan_fingerprint(recipe_names, week_start)
    if st.session_state.get("weekly_plan_saved_fingerprint") != fingerprint:
        return None
    saved_name = st.session_state.get("weekly_plan_last_saved_name")
    if not saved_name:
        return None
    return SavedWeeklyPlan(
        week_start=week_start,
        version=0,
        name=str(saved_name),
        recipes=recipes,
    )


def _invalidate_weekly_plan_save_state() -> None:
    st.session_state.pop("weekly_plan_last_saved_name", None)
    st.session_state.pop("weekly_plan_saved_fingerprint", None)
    st.session_state.pop(_OVERWRITE_CONFIRM_FP_KEY, None)
    st.session_state.pop(_RUN_GROCERY_AFTER_OVERWRITE_KEY, None)


def _sync_weekly_plan_save_state(recipe_names: list[str], plan: SavedWeeklyPlan) -> None:
    st.session_state.weekly_plan_last_saved_name = plan.name
    st.session_state.weekly_plan_saved_fingerprint = _weekly_plan_fingerprint(
        recipe_names, plan.week_start
    )


def _overwrite_confirm_fingerprint(recipe_names: list[str]) -> tuple[str, ...]:
    return _weekly_plan_fingerprint(recipe_names, _resolve_save_week_start())


def _weekly_plan_overwrite_confirmed(recipe_names: list[str]) -> bool:
    return st.session_state.get(_OVERWRITE_CONFIRM_FP_KEY) == _overwrite_confirm_fingerprint(
        recipe_names
    )


def _weekly_plan_save_would_replace(
    recipe_names: list[str],
) -> tuple[bool, SavedWeeklyPlan | None]:
    recipes = normalize_recipe_names(recipe_names)
    if not recipes:
        return False, None
    week_start = _resolve_save_week_start()
    existing = find_plan_for_week(week_start, recipes_db=get_db())
    if existing is None or existing.recipes == recipes:
        return False, existing
    return True, existing


def _plan_recipe_diff_markdown(
    *,
    previous: tuple[str, ...],
    new_names: list[str],
) -> tuple[list[str], list[str]]:
    new_keys = {recipe_lookup_key(name) for name in new_names}
    old_keys = {recipe_lookup_key(name) for name in previous}
    removed = [name for name in previous if recipe_lookup_key(name) not in new_keys]
    added = [name for name in new_names if recipe_lookup_key(name) not in old_keys]
    return removed, added


def _render_weekly_plan_overwrite_prompt(
    recipe_names: list[str],
    existing: SavedWeeklyPlan,
    *,
    confirm_button_key: str,
) -> None:
    removed, added = _plan_recipe_diff_markdown(previous=existing.recipes, new_names=recipe_names)
    st.warning(
        f"This will **replace** the saved plan for the week of "
        f"**{existing.week_start.isoformat()}** in Notion "
        f"({len(existing.recipes)} meals saved now → {len(recipe_names)} in your list)."
    )
    if removed:
        st.markdown("**Removing:** " + ", ".join(removed))
    if added:
        st.markdown("**Adding:** " + ", ".join(added))
    if st.button("Replace saved plan for this week", type="primary", key=confirm_button_key):
        st.session_state[_OVERWRITE_CONFIRM_FP_KEY] = _overwrite_confirm_fingerprint(recipe_names)
        st.rerun()


def _apply_weekly_plan_save_result(
    result: WeeklyPlanSaveResult,
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None,
) -> None:
    save_week_plan(recipe_names, WEEK_PLAN_PATH)
    _sync_weekly_plan_save_state(recipe_names, result.plan)
    if result.outcome == "unchanged":
        return
    invalidate_saved_plans_cache()
    updated_stats = sync_plan_selection_stats(
        get_db(),
        result.previous_recipes,
        recipe_names,
        cached_recipes=cached_recipes,
    )
    if updated_stats:
        invalidate_notion_cache()
    st.session_state.pop(_OVERWRITE_CONFIRM_FP_KEY, None)


def _persist_weekly_plan_to_notion(
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
    require_overwrite_confirm: bool = True,
    overwrite_confirm_key: str = "weekly_plan_confirm_overwrite",
) -> SavedWeeklyPlan | None:
    """Write the plan to Notion unless blocked on overwrite confirmation."""
    if _weekly_plan_mode() == "dev" or not recipe_names:
        return None
    if _matching_saved_plan(recipe_names) is not None:
        return _matching_saved_plan(recipe_names)

    would_replace, existing = _weekly_plan_save_would_replace(recipe_names)
    if (
        require_overwrite_confirm
        and would_replace
        and existing is not None
        and not _weekly_plan_overwrite_confirmed(recipe_names)
    ):
        _render_weekly_plan_overwrite_prompt(
            recipe_names,
            existing,
            confirm_button_key=overwrite_confirm_key,
        )
        return None

    result = ensure_saved_weekly_plan(
        recipe_names,
        recipes_db=get_db(),
        week_choice=_save_week_choice(),
        cached_recipes=cached_recipes,
    )
    _apply_weekly_plan_save_result(result, recipe_names, cached_recipes=cached_recipes)
    return result.plan


def _commit_weekly_plan_to_notion(
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> SavedWeeklyPlan | None:
    """Ensure plan exists in Notion and refresh local week_plan.json for diversity hints."""
    return _persist_weekly_plan_to_notion(recipe_names, cached_recipes=cached_recipes)


def _ensure_weekly_plan_saved_before_grocery(
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> bool:
    """Auto-save before grocery. Returns False when overwrite confirmation is pending."""
    if _weekly_plan_mode() == "dev" or not recipe_names:
        return True
    if _matching_saved_plan(recipe_names) is not None:
        return True
    plan = _persist_weekly_plan_to_notion(
        recipe_names,
        cached_recipes=cached_recipes,
        overwrite_confirm_key="weekly_plan_confirm_overwrite_grocery",
    )
    return plan is not None


def _render_save_plan_controls(
    recipe_names: list[str],
    *,
    cached_recipes: list[Recipe] | None = None,
) -> None:
    """Explicit save after meal generation (not used in dev mode)."""
    mode = _weekly_plan_mode()
    if mode == "dev" or not recipe_names:
        return

    _render_save_week_choice_buttons()

    existing = _matching_saved_plan(recipe_names)
    if existing is not None:
        st.success(f"Plan saved as **{existing.name}**")
        return

    would_replace, existing = _weekly_plan_save_would_replace(recipe_names)
    if (
        would_replace
        and existing is not None
        and not _weekly_plan_overwrite_confirmed(recipe_names)
    ):
        _render_weekly_plan_overwrite_prompt(
            recipe_names,
            existing,
            confirm_button_key="weekly_plan_confirm_overwrite_save",
        )
        return

    label = "Save plan to Notion"
    if st.button(label, type="secondary", key="save_weekly_plan"):
        with loading_indicator("Saving plan to Notion…"):
            plan = _commit_weekly_plan_to_notion(recipe_names, cached_recipes=cached_recipes)
        if plan is not None:
            st.success(f"Plan saved as **{plan.name}**")
        return


def _invalidate_stale_grocery_result() -> None:
    """Drop cached grocery results when the meal plan has changed."""
    stash_gen = st.session_state.get(GROCERY_STASH_NOTION_GENERATION_KEY)
    if stash_gen is not None and int(stash_gen) != notion_cache_generation():
        _clear_grocery_result(clear_pre_extra_items=False)

    current_plan = tuple(_current_plan_names())
    current_fp = recipe_review_plan_fingerprint(list(current_plan))

    review_fp = st.session_state.get("grocery_review_plan_fingerprint")
    if review_fp is not None and review_fp != current_fp:
        _clear_grocery_result(clear_pre_extra_items=False)

    result = st.session_state.get("grocery_result")
    if not result:
        return

    cached_plan = result.get("week_plan")
    if cached_plan is not None and cached_plan != current_plan:
        _clear_grocery_result()
