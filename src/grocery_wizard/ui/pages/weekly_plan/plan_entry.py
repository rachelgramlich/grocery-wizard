"""Weekly plan entry (new / saved / dev) and meal-plan building UI."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

from src.grocery_wizard.config import load_config
from src.grocery_wizard.integrations.notion import ColumnInfo, NotionRecipesDB
from src.grocery_wizard.planning.meal_planner import (
    MealPlanFilters,
    build_ingredient_index,
    default_filters,
    filter_recipes,
    replace_meals_in_plan,
    suggest_meals,
)
from src.grocery_wizard.planning.saved_weekly_plans import load_plan_recipes
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    filter_recipes_for_manual_pick,
    increment_suggestion_rejections,
    meal_plan_status_column_name,
    origins_after_swap,
    rejection_names_from_swap,
    resolve_slot_origins_for_plan,
    suggestion_rejections_column_name,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.dev_jumps import (
    DEFAULT_DEV_MEAL_COUNT,
    DEV_JUMP_CAPTIONS,
    DEV_JUMP_FLOW_ORDER,
    DEV_MANUAL_RECIPES_KEY,
    DevJumpTarget,
    commit_dev_jump,
    dev_jump_display_title,
    resolve_dev_jump_meal_names,
    sync_dev_manual_multiselect,
)
from src.grocery_wizard.ui.ids import BLOCK_WEEKLY_MEALS
from src.grocery_wizard.ui.loading import loading_indicator
from src.grocery_wizard.ui.meal_plan_filters import (
    recipes_ingredient_cache_key,
    render_meal_plan_filters,
)
from src.grocery_wizard.ui.notion_cache import cached_saved_plans, invalidate_notion_cache
from src.grocery_wizard.ui.pages.weekly_plan.state import (
    PLAN_FORCE_OPEN_1A_KEY,
    PLAN_MEAL_COUNT_WIDGET_KEY,
    _clear_grocery_result,
    _clear_grocery_session_overrides,
    _current_plan_names,
    _invalidate_weekly_plan_save_state,
    _plan_slot_origins,
    _render_save_plan_controls,
    _reset_weekly_plan_workflow,
    _set_plan_slot_origins,
    _weekly_plan_mode,
    _weekly_plan_mode_choices,
    _weekly_plan_persists_tracking_stats_to_notion,
    _write_plan_names,
)
from src.grocery_wizard.ui.pages.weekly_plan.step_ui import (
    WeeklyRailStep,
    queue_weekly_scroll,
    set_expanded_step,
)
from src.grocery_wizard.ui.recipe_match import (
    render_unmatched_plan_recipes_help,
    unmatched_plan_recipe_names,
)


def _meal_plan_picker_columns(db: NotionRecipesDB) -> tuple[str | None, str | None]:
    return (
        meal_plan_status_column_name(db),
        suggestion_rejections_column_name(db),
    )


def _manual_pick_recipes(all_recipes: list, db: NotionRecipesDB) -> list:
    status_column, _ = _meal_plan_picker_columns(db)
    return filter_recipes_for_manual_pick(all_recipes, status_column=status_column)


def _locked_recipes_for_plan_build(*, meal_count: int) -> list[str]:
    """Pinned meals for auto-fill: pre-build picks plus saved-plan loaded meals (#105)."""
    locked: list[str] = []
    for name in st.session_state.get("plan_prebuild_pinned_recipes") or []:
        if name and name not in locked:
            locked.append(name)
    if _weekly_plan_mode() == "saved":
        for name in _current_plan_names():
            if name not in locked:
                locked.append(name)
    return locked[: int(meal_count)]


def _clamp_prebuild_pinned_recipes(*, max_pins: int) -> None:
    """Keep pre-build pins within meal count (e.g. after lowering meal count)."""
    key = "plan_prebuild_pinned_recipes"
    pinned = list(st.session_state.get(key) or [])
    if not pinned:
        return
    limit = max(1, int(max_pins))
    if len(pinned) <= limit:
        return
    st.session_state[key] = pinned[:limit]


def _append_prebuild_pin(recipe_name: str, *, max_pins: int) -> None:
    pinned = list(st.session_state.get("plan_prebuild_pinned_recipes") or [])
    if recipe_name in pinned:
        st.warning("That recipe is already pinned.")
        return
    if len(pinned) >= max(1, int(max_pins)):
        st.warning(f"You can pin at most {max_pins} meals for this week.")
        return
    pinned.append(recipe_name)
    st.session_state.plan_prebuild_pinned_recipes = pinned
    st.rerun()


def _remove_prebuild_pin(recipe_name: str) -> None:
    pinned = list(st.session_state.get("plan_prebuild_pinned_recipes") or [])
    if recipe_name not in pinned:
        return
    st.session_state.plan_prebuild_pinned_recipes = [name for name in pinned if name != recipe_name]
    st.rerun()


def _render_direct_recipe_pick(
    all_names: list[str],
    *,
    selectbox_key: str,
    apply_button_key: str,
    apply_button_label: str,
    on_apply: Callable[[str], None],
) -> None:
    st.markdown("**Pick a recipe**")
    if not all_names:
        st.warning("No recipes in Notion yet.")
        return
    direct_picked = st.selectbox(
        "Choose recipe",
        all_names,
        index=None,
        placeholder="Search or pick a recipe…",
        key=selectbox_key,
        label_visibility="collapsed",
    )
    if st.button(apply_button_label, key=apply_button_key):
        if not direct_picked:
            st.warning("Choose a recipe first.")
        else:
            with loading_indicator("Applying recipe…"):
                on_apply(direct_picked)


def _render_filtered_recipe_picker(
    *,
    all_recipes: list,
    filter_columns: list[ColumnInfo],
    filter_defaults: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    ingredient_index: dict[str, set[str]],
    key_prefix: str,
    selectbox_key: str,
    apply_button_key: str,
    apply_button_label: str,
    on_apply: Callable[[str], None],
    filter_caption: str | None = None,
) -> None:
    """Shared filter widgets + filtered recipe selectbox + confirm action."""
    if filter_caption:
        st.caption(filter_caption)
    active_filters = render_meal_plan_filters(
        filter_columns,
        filter_defaults,
        key_prefix=key_prefix,
        ingredient_index=ingredient_index,
    )
    pool = filter_recipes(
        all_recipes,
        active_filters,
        schema_columns,
        ingredient_index=ingredient_index,
    )
    matching_names = [recipe.name for recipe in pool]
    with st.container(border=True):
        st.markdown("**Matching recipes**")
        st.caption("Recipes that match the filters above.")
        if not matching_names:
            st.warning("No recipes match these filters.")
            return
        picked = st.selectbox(
            "Recipe",
            matching_names,
            index=None,
            placeholder="Pick from filtered recipes…",
            key=selectbox_key,
            label_visibility="collapsed",
        )
        if st.button(apply_button_label, key=apply_button_key):
            if not picked:
                st.warning("Choose a recipe from the filtered list first.")
            else:
                with loading_indicator("Applying recipe…"):
                    on_apply(picked)


def _render_prebuild_recipe_picker(
    all_recipes: list,
    *,
    meal_count: int,
    filter_columns: list[ColumnInfo],
    filter_defaults: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    ingredient_index: dict[str, set[str]],
) -> None:
    """Single expander: filter → pin → repeat, before **Build my plan**."""
    db = get_db()
    manual_recipes = _manual_pick_recipes(all_recipes, db)
    all_names = sorted({recipe.name for recipe in manual_recipes}, key=str.lower)
    max_pins = max(1, int(meal_count))
    current = _current_plan_names()
    if "plan_prebuild_pinned_recipes" not in st.session_state and current:
        st.session_state.plan_prebuild_pinned_recipes = list(current)[:max_pins]
    _clamp_prebuild_pinned_recipes(max_pins=max_pins)
    pinned = list(st.session_state.get("plan_prebuild_pinned_recipes") or [])

    if not all_names:
        st.caption("No recipes in Notion yet — add recipes to pin meals before building.")
        return

    with st.expander("Choose recipe manually", expanded=False):
        st.caption(
            "Pick a recipe directly or use filters, then pin. Repeat until "
            "you have as many locked meals as you want."
        )
        _render_direct_recipe_pick(
            all_names,
            selectbox_key="plan_prebuild_direct_pick",
            apply_button_key="plan_prebuild_pin_direct",
            apply_button_label="Pin this recipe",
            on_apply=lambda name: _append_prebuild_pin(name, max_pins=max_pins),
        )
        st.divider()
        st.markdown("**Or filter**")
        _render_filtered_recipe_picker(
            all_recipes=manual_recipes,
            filter_columns=filter_columns,
            filter_defaults=filter_defaults,
            schema_columns=schema_columns,
            ingredient_index=ingredient_index,
            key_prefix="plan_prebuild_filter",
            selectbox_key="plan_prebuild_filtered_pick",
            apply_button_key="plan_prebuild_pin_recipe",
            apply_button_label="Pin this recipe",
            on_apply=lambda name: _append_prebuild_pin(name, max_pins=max_pins),
            filter_caption="Optional — narrow the list using the filters below.",
        )

    if pinned:
        st.markdown("**Pinned meals**")
        st.caption(
            f"{len(pinned)} of {max_pins} slots pinned — remove any you change your mind on."
        )
        for index, name in enumerate(pinned):
            pin_col, remove_col = st.columns([8, 1])
            with pin_col:
                st.write(name)
            with remove_col:
                if st.button("Remove", key=f"plan_prebuild_unpin_{index}", help="Unpin this meal"):
                    _remove_prebuild_pin(name)


def _set_plan_slot_recipe(plan: list[str], slot_index: int, recipe_name: str) -> list[str]:
    updated = list(plan)
    while len(updated) < slot_index:
        updated.append("")
    updated[slot_index - 1] = recipe_name
    return updated


def _slot_manual_picker_fragment(
    slot_index: int,
) -> Callable[..., None]:
    @st.fragment(key=f"plan_slot_manual_{slot_index}")
    def _render(
        *,
        all_recipes: list,
        filter_columns: list[ColumnInfo],
        filter_defaults: MealPlanFilters,
        schema_columns: dict[str, ColumnInfo],
        ingredient_index: dict[str, set[str]],
    ) -> None:

        def _apply_picked(recipe_name: str) -> None:
            updated = _set_plan_slot_recipe(_current_plan_names(), slot_index, recipe_name)
            _write_plan_names(updated)
            origins = _plan_slot_origins()
            while len(origins) < len(updated):
                origins.append("suggested")
            origins[slot_index - 1] = "manual"
            _set_plan_slot_origins(origins)
            _invalidate_weekly_plan_save_state()
            _clear_grocery_session_overrides()
            _clear_grocery_result()
            st.rerun()

        db = get_db()
        pick_pool = _manual_pick_recipes(all_recipes, db)
        all_names = sorted({recipe.name for recipe in pick_pool}, key=str.lower)

        _render_direct_recipe_pick(
            all_names,
            selectbox_key=f"plan_slot_direct_pick_{slot_index}",
            apply_button_key=f"plan_slot_apply_direct_{slot_index}",
            apply_button_label="Use this recipe",
            on_apply=_apply_picked,
        )

        st.divider()
        st.markdown("**Or filter**")
        _render_filtered_recipe_picker(
            all_recipes=pick_pool,
            filter_columns=filter_columns,
            filter_defaults=filter_defaults,
            schema_columns=schema_columns,
            ingredient_index=ingredient_index,
            key_prefix=f"plan_slot_{slot_index}",
            selectbox_key=f"plan_slot_pick_{slot_index}",
            apply_button_key=f"plan_slot_apply_{slot_index}",
            apply_button_label="Use this recipe",
            on_apply=_apply_picked,
            filter_caption="Optional — narrow the list using the filters below.",
        )

    return _render


def _render_slot_manual_popover(
    *,
    slot_index: int,
    all_recipes: list,
    filter_columns: list[ColumnInfo],
    filter_defaults: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    ingredient_index: dict[str, set[str]],
) -> None:
    with st.popover(
        "Choose manually",
        help="Pick a recipe for this meal slot (search or filter)",
        width="content",
        wrap=False,
    ):
        st.caption("Filters apply to this meal slot only.")
        _slot_manual_picker_fragment(slot_index)(
            all_recipes=all_recipes,
            filter_columns=filter_columns,
            filter_defaults=filter_defaults,
            schema_columns=schema_columns,
            ingredient_index=ingredient_index,
        )


def _render_dev_jump_tools(db: NotionRecipesDB) -> None:
    """Collapsed dev-only shortcuts to wizard steps for manual UAT."""
    if _weekly_plan_mode() != "dev":
        return

    with st.expander("Dev tools", expanded=False):
        st.caption(
            "Jump to a wizard step using a small default meal set from Notion "
            "(recipes with ingredients). Use when manually testing UI without "
            "clicking through meal generation each time."
        )

        def _dev_jump_bullet(target: DevJumpTarget) -> None:
            title = dev_jump_display_title(target)
            st.markdown(f"- **{title}** — {DEV_JUMP_CAPTIONS[target]}")

        meal_count = int(st.session_state.get("plan_meal_count", DEFAULT_DEV_MEAL_COUNT))

        def _dev_jump_button(
            target: DevJumpTarget,
            *,
            label: str,
            key_suffix: str,
            names: list[str],
            require_names: bool = False,
        ) -> None:
            if not st.button(label, key=f"dev_jump_{target.value}_{key_suffix}"):
                return
            if require_names and not names:
                st.warning("Pick at least one recipe for the manual meals jump.")
                return
            names = commit_dev_jump(st.session_state, db, target, names)
            if not names:
                st.error(
                    "No recipes in Notion to use for dev jump. Add recipes with ingredients first."
                )
                return
            st.session_state.plan_prebuild_pinned_recipes = list(names)
            st.rerun()

        for step in DEV_JUMP_FLOW_ORDER:
            _dev_jump_bullet(step)

        all_names = sorted({recipe.name for recipe in db.query_recipes()}, key=str.lower)
        manual_pick = st.multiselect(
            "Choose recipes manually",
            options=all_names,
            key=DEV_MANUAL_RECIPES_KEY,
            placeholder="Pick one or more recipes…",
            help="When set, updates **1b. Your meals** immediately and is used by every jump "
            "button below except **Meals filled: auto**.",
        )
        sync_dev_manual_multiselect(st.session_state)

        auto_names = resolve_dev_jump_meal_names(
            st.session_state,
            db,
            meal_count=meal_count,
            force_auto=True,
        )
        jump_names = resolve_dev_jump_meal_names(
            st.session_state,
            db,
            meal_count=meal_count,
        )
        _dev_jump_button(
            DevJumpTarget.MEALS_FILLED,
            label="Meals filled: auto",
            key_suffix="auto",
            names=auto_names,
        )
        _dev_jump_button(
            DevJumpTarget.MEALS_FILLED,
            label="Meals filled: manual",
            key_suffix="manual",
            names=list(manual_pick),
            require_names=True,
        )
        _dev_jump_button(
            DevJumpTarget.PRE_BUILD_GROCERY,
            label="Dev: Pre-build grocery",
            key_suffix="btn_pre_build",
            names=jump_names,
        )
        _dev_jump_button(
            DevJumpTarget.PER_RECIPE_REVIEW,
            label="Dev: Per-recipe review",
            key_suffix="btn_review",
            names=jump_names,
        )
        _dev_jump_button(
            DevJumpTarget.GROCERY_RESULT,
            label="Dev: Final list",
            key_suffix="btn_final_list",
            names=jump_names,
        )


def _render_weekly_plan_entry() -> bool:
    """Prompt for new / saved / dev mode. Returns True when the user may continue planning."""
    mode = _weekly_plan_mode()
    if mode is not None:
        labels = {
            "new": "New weekly plan",
            "saved": "Continue from a saved plan",
            "dev": "Dev mode (do not save)",
        }
        loaded = st.session_state.get("weekly_plan_loaded_name")
        detail = f" — loaded **{loaded}**" if mode == "saved" and loaded else ""
        st.info(f"**{labels[mode]}**{detail}")
        if st.button("Change how I started", key="weekly_plan_change_mode"):
            from src.grocery_wizard.ui.pages.weekly_plan.step_ui import clear_expanded_step_override

            _reset_weekly_plan_workflow(clear_mode=True)
            st.session_state.weekly_plan_mode_choice = "new"
            clear_expanded_step_override()
            st.rerun()
        return True

    st.markdown("### How do you want to start?")
    mode_options = _weekly_plan_mode_choices()
    choice = st.radio(
        "Weekly plan session",
        options=mode_options,
        format_func=lambda value: {
            "new": "Start a new weekly plan",
            "saved": "Continue a saved weekly plan",
            "dev": "Dev mode (nothing saved to Notion)",
        }[value],
        key="weekly_plan_mode_choice",
        label_visibility="collapsed",
    )
    st.caption(
        "New plans can be saved anytime. Saved plans reload your meals; "
        "grocery lists stay in this session."
    )

    config = load_config()
    db = get_db()
    saved_plans = cached_saved_plans(
        db,
        weekly_plans_database_id=config.notion_weekly_meal_plans_database_id,
    )
    selected_plan_name: str | None = None
    if choice == "saved":
        if not saved_plans:
            st.warning("No saved weekly plans yet. Start a new list first.")
        else:
            options = [plan.name for plan in saved_plans]

            def _saved_plan_label(plan_name: str) -> str:
                for plan in saved_plans:
                    if plan.name == plan_name:
                        return f"Week of {plan.week_start.isoformat()} ({len(plan.recipes)} meals)"
                return plan_name

            selected_plan_name = st.selectbox(
                "Saved plan",
                options,
                format_func=_saved_plan_label,
                key="weekly_plan_saved_name_pick",
            )

    if choice == "dev":
        st.session_state.weekly_plan_mode = "dev"
        set_expanded_step(WeeklyRailStep.PLAN_MEALS)
        _reset_weekly_plan_workflow(clear_mode=False)
        st.session_state.plan_meals_text = ""
        st.session_state.plan_meal_count = 1
        st.session_state.pop(PLAN_MEAL_COUNT_WIDGET_KEY, None)
        st.rerun()

    if st.button("Continue", type="primary", key="weekly_plan_mode_continue"):
        if choice == "saved" and not saved_plans:
            return False
        st.session_state.weekly_plan_mode = choice
        set_expanded_step(WeeklyRailStep.PLAN_MEALS)
        _reset_weekly_plan_workflow(clear_mode=False)
        if choice == "saved" and selected_plan_name:
            with loading_indicator("Loading saved plan from Notion…"):
                st.session_state.plan_meals_text = "\n".join(
                    load_plan_recipes(selected_plan_name, recipes_db=get_db())
                )
            st.session_state.weekly_plan_loaded_name = selected_plan_name
        elif choice == "new":
            st.session_state.plan_meals_text = ""
            st.session_state.plan_meal_count = load_config().default_meals
            st.session_state.pop(PLAN_MEAL_COUNT_WIDGET_KEY, None)
        queue_weekly_scroll(BLOCK_WEEKLY_MEALS)
        st.rerun()

    return False


def _ensure_plan_session_defaults() -> None:
    if "plan_meals_text" not in st.session_state:
        st.session_state.plan_meals_text = ""
    if "plan_meal_count" not in st.session_state:
        st.session_state.plan_meal_count = (
            1 if _weekly_plan_mode() == "dev" else load_config().default_meals
        )


def _sync_plan_meal_count_widget_from_persisted() -> None:
    if PLAN_MEAL_COUNT_WIDGET_KEY not in st.session_state:
        st.session_state[PLAN_MEAL_COUNT_WIDGET_KEY] = int(st.session_state.plan_meal_count)


def _render_meal_count_input() -> int:
    st.markdown("### 1. Meals")
    _sync_plan_meal_count_widget_from_persisted()
    meal_count = int(
        st.number_input(
            "How many meals this week?",
            min_value=1,
            max_value=21,
            step=1,
            key=PLAN_MEAL_COUNT_WIDGET_KEY,
            on_change=_apply_plan_meal_count_from_widget,
        )
    )
    st.session_state.plan_meal_count = meal_count
    return meal_count


def _cached_plan_ingredient_index(all_recipes: list) -> dict[str, set[str]]:
    recipes_cache_key = recipes_ingredient_cache_key(all_recipes)
    cached_index = st.session_state.get("_ingredient_index")
    if st.session_state.get("_ingredient_index_key") != recipes_cache_key or cached_index is None:
        st.session_state["_ingredient_index_key"] = recipes_cache_key
        st.session_state["_ingredient_index"] = build_ingredient_index(all_recipes)
    return st.session_state["_ingredient_index"]


def _render_generate_plan_controls(
    db: NotionRecipesDB,
    *,
    all_recipes: list,
    meal_count: int,
    ingredient_index: dict[str, set[str]],
    show_section_heading: bool = True,
) -> MealPlanFilters:
    schema = db.schema
    filter_defaults = default_filters(schema.all_columns)

    if show_section_heading:
        st.markdown("#### 1a. Build your meal list")
    st.caption(
        "Optionally pin meals you already know, then **Build my plan** auto-fills the rest. "
        "Per-meal filters are available under each meal after you build."
    )
    filter_columns = [*schema.filter_columns, *schema.checkbox_columns]
    build_filters = default_filters(schema.all_columns)

    _render_prebuild_recipe_picker(
        all_recipes,
        meal_count=int(meal_count),
        filter_columns=filter_columns,
        filter_defaults=filter_defaults,
        schema_columns=schema.all_columns,
        ingredient_index=ingredient_index,
    )

    if st.button(
        "Build my plan",
        type="primary",
        key="build_plan",
        help="Keeps pinned meals and suggests diverse recipes for any open slots.",
    ):
        with loading_indicator("Building your meal plan…"):
            locked_for_build = _locked_recipes_for_plan_build(meal_count=int(meal_count))
            locked_set = set(locked_for_build)
            status_column, rejections_column = _meal_plan_picker_columns(db)
            plan = suggest_meals(
                all_recipes,
                meals=int(meal_count),
                locked_names=locked_for_build,
                filters=build_filters,
                schema_columns=schema.all_columns,
                ingredient_index=ingredient_index,
                status_column=status_column,
                rejections_column=rejections_column,
            )
            _write_plan_names(plan)
            _set_plan_slot_origins(
                resolve_slot_origins_for_plan(plan, locked_names=locked_set),
            )
            st.session_state.plan_rejected_names = []
            _invalidate_weekly_plan_save_state()
            _clear_grocery_session_overrides()
            _clear_grocery_result()
            st.session_state.plan_last_week_filters = build_filters
        queue_weekly_scroll(BLOCK_WEEKLY_MEALS)
        st.rerun()

    return build_filters


def _render_built_plan_meals(
    db: NotionRecipesDB,
    *,
    all_recipes: list,
    meal_count: int,
    week_filters: MealPlanFilters,
    ingredient_index: dict[str, set[str]],
) -> None:
    schema = db.schema
    filter_defaults = default_filters(schema.all_columns)
    filter_columns = [*schema.filter_columns, *schema.checkbox_columns]

    suggestion_pool = filter_recipes(
        all_recipes, week_filters, schema.all_columns, ingredient_index=ingredient_index
    )
    status_column, rejections_column = _meal_plan_picker_columns(db)

    current_plan = _current_plan_names()
    if not current_plan:
        return

    def _apply_plan_swap(names_to_replace: list[str]) -> None:
        with loading_indicator("Updating your meals…"):
            origins = _plan_slot_origins()
            stats_targets = rejection_names_from_swap(current_plan, names_to_replace, origins)
            rejected = set(st.session_state.get("plan_rejected_names", []))
            new_plan, rejected = replace_meals_in_plan(
                current_plan,
                names_to_replace,
                all_recipes=all_recipes,
                pool=suggestion_pool,
                rejected_names=rejected,
                status_column=status_column,
                rejections_column=rejections_column,
            )
            if stats_targets and _weekly_plan_persists_tracking_stats_to_notion():
                updated_stats = increment_suggestion_rejections(
                    db,
                    stats_targets,
                    cached_recipes=all_recipes,
                )
                if updated_stats:
                    invalidate_notion_cache()
            _write_plan_names(new_plan)
            _set_plan_slot_origins(
                origins_after_swap(current_plan, names_to_replace, origins, new_plan),
            )
            st.session_state.plan_rejected_names = sorted(rejected)
            _invalidate_weekly_plan_save_state()
            _clear_grocery_session_overrides()
            _clear_grocery_result()
        st.rerun()

    st.markdown("#### 1b. Your meals")
    render_unmatched_plan_recipes_help(
        unmatched_plan_recipe_names(current_plan, all_recipes),
        context="meals",
    )
    st.markdown('<p class="gw-meal-slot-list" aria-hidden="true"></p>', unsafe_allow_html=True)
    for index, name in enumerate(current_plan, start=1):
        # Ratio is a hint; theme CSS sizes the action column to its buttons.
        meal_col, actions_col = st.columns([1, 1], vertical_alignment="top")
        with meal_col:
            st.markdown(
                f'<p class="gw-meal-slot-label">'
                f'<span class="gw-meal-slot-title">{index}.</span> '
                f'<span class="gw-meal-slot-recipe">{html.escape(name)}</span></p>',
                unsafe_allow_html=True,
            )
        with (
            actions_col,
            st.container(
                key=f"meal_slot_action_row_{index}",
                horizontal=True,
                gap="small",
                wrap=False,
                width="content",
                horizontal_alignment="left",
            ),
        ):
            if st.button(
                "Quick swap",
                key=f"swap_meal_{index}",
                width="content",
                help="Suggest a different recipe from this week's filter pool",
            ):
                _apply_plan_swap([name])
            _render_slot_manual_popover(
                slot_index=index,
                all_recipes=all_recipes,
                filter_columns=filter_columns,
                filter_defaults=filter_defaults,
                schema_columns=schema.all_columns,
                ingredient_index=ingredient_index,
            )

    fill_remaining = len(current_plan) < int(meal_count)
    with st.container(key="plan_week_action_row"):
        st.markdown(
            '<p class="gw-plan-week-actions" aria-hidden="true"></p>',
            unsafe_allow_html=True,
        )
        with st.container(
            horizontal=True,
            gap="medium",
            wrap=False,
            width="content",
            horizontal_alignment="left",
        ):
            if st.button(
                "Change filters & rebuild",
                key="plan_jump_to_builder",
                width="content",
                help=(
                    "Opens plan builder: adjust week filters or pinned meals, then Build my plan."
                ),
            ):
                st.session_state[PLAN_FORCE_OPEN_1A_KEY] = True
                st.rerun()
            if st.button("Re-generate all meals", key="regenerate_plan", width="content"):
                with loading_indicator("Re-generating your meal plan…"):
                    origins = _plan_slot_origins()
                    stats_targets = rejection_names_from_swap(current_plan, current_plan, origins)
                    if stats_targets and _weekly_plan_persists_tracking_stats_to_notion():
                        updated_stats = increment_suggestion_rejections(
                            db,
                            stats_targets,
                            cached_recipes=all_recipes,
                        )
                        if updated_stats:
                            invalidate_notion_cache()
                    rejected = set(st.session_state.get("plan_rejected_names", []))
                    plan = suggest_meals(
                        all_recipes,
                        meals=int(meal_count),
                        locked_names=[],
                        filters=week_filters,
                        schema_columns=schema.all_columns,
                        rejected_names=rejected,
                        ingredient_index=ingredient_index,
                        status_column=status_column,
                        rejections_column=rejections_column,
                    )
                    _write_plan_names(plan)
                    _set_plan_slot_origins(["suggested"] * len(plan))
                    _invalidate_weekly_plan_save_state()
                    _clear_grocery_session_overrides()
                    _clear_grocery_result()
                st.rerun()
            if fill_remaining and st.button(
                "Fill remaining slots", key="fill_remaining_plan", width="content"
            ):
                with loading_indicator("Filling remaining meal slots…"):
                    plan = suggest_meals(
                        all_recipes,
                        meals=int(meal_count),
                        locked_names=current_plan,
                        filters=week_filters,
                        schema_columns=schema.all_columns,
                        ingredient_index=ingredient_index,
                        status_column=status_column,
                        rejections_column=rejections_column,
                    )
                    _write_plan_names(plan)
                    origins = _plan_slot_origins()
                    new_origins = [
                        origins[i] if i < len(origins) else "suggested" for i in range(len(plan))
                    ]
                    while len(new_origins) < len(plan):
                        new_origins.append("suggested")
                    _set_plan_slot_origins(new_origins[: len(plan)])
                    _invalidate_weekly_plan_save_state()
                    _clear_grocery_session_overrides()
                    _clear_grocery_result()
                st.rerun()

    st.divider()
    st.markdown("#### 1c. Save your plan")
    st.caption(
        "When your meal list looks good, save it to Notion. "
        "That finishes this step before you build a grocery list."
    )
    with st.container(key="weekly_meals_save"):
        _render_save_plan_controls(_current_plan_names(), cached_recipes=all_recipes)


def _apply_plan_meal_count_from_widget() -> None:
    """``on_change`` for the meal-count widget (runs before the fragment body)."""
    st.session_state.plan_meal_count = int(st.session_state[PLAN_MEAL_COUNT_WIDGET_KEY])


def _sync_plan_length_to_meal_count(meal_count: int) -> None:
    """Keep pinned meals and built plan length aligned with the meal-count widget."""
    _clamp_prebuild_pinned_recipes(max_pins=max(1, int(meal_count)))
    names = _current_plan_names()
    if len(names) <= int(meal_count):
        return
    _write_plan_names(names[: int(meal_count)])
    _invalidate_weekly_plan_save_state()
    _clear_grocery_session_overrides()
    _clear_grocery_result()


def render_meals_section(
    db: NotionRecipesDB,
    *,
    all_recipes: list,
    meal_count: int,
) -> list[str]:
    """Render step 1 (meals) and return the current planned recipe names."""
    _render_dev_jump_tools(db)

    ingredient_index = _cached_plan_ingredient_index(all_recipes)
    current_plan = _current_plan_names()
    fallback_filters = default_filters(db.schema.all_columns)
    stored_filters = st.session_state.get("plan_last_week_filters", fallback_filters)
    has_plan = bool(current_plan)
    force_open_1a = st.session_state.pop(PLAN_FORCE_OPEN_1A_KEY, False)
    expanded_1a = (not has_plan) or force_open_1a

    if has_plan:
        with st.expander("1a. Build your meal list", expanded=expanded_1a):
            week_filters = _render_generate_plan_controls(
                db,
                all_recipes=all_recipes,
                meal_count=meal_count,
                ingredient_index=ingredient_index,
                show_section_heading=False,
            )
    else:
        week_filters = _render_generate_plan_controls(
            db,
            all_recipes=all_recipes,
            meal_count=meal_count,
            ingredient_index=ingredient_index,
            show_section_heading=True,
        )
    st.session_state.plan_last_week_filters = week_filters

    _render_built_plan_meals(
        db,
        all_recipes=all_recipes,
        meal_count=meal_count,
        week_filters=stored_filters if has_plan else week_filters,
        ingredient_index=ingredient_index,
    )

    return _current_plan_names()
