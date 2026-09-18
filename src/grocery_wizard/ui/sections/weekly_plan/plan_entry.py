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
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.dev_jumps import (
    DEFAULT_DEV_MEAL_COUNT,
    DEV_JUMP_CAPTIONS,
    DEV_JUMP_FLOW_ORDER,
    DevJumpTarget,
    commit_dev_jump,
    dev_jump_display_title,
    pick_default_recipe_names,
)
from src.grocery_wizard.ui.meal_plan_filters import (
    recipes_ingredient_cache_key,
    render_meal_plan_filters,
)
from src.grocery_wizard.ui.notion_cache import cached_saved_plans
from src.grocery_wizard.ui.recipe_match import (
    render_unmatched_plan_recipes_help,
    unmatched_plan_recipe_names,
)
from src.grocery_wizard.ui.sections.weekly_plan.state import (
    _clear_grocery_result,
    _clear_grocery_session_overrides,
    _current_plan_names,
    _invalidate_weekly_plan_save_state,
    _render_save_plan_controls,
    _reset_weekly_plan_workflow,
    _weekly_plan_mode,
    _weekly_plan_mode_choices,
    _write_plan_names,
)


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
    all_names = sorted({recipe.name for recipe in all_recipes}, key=str.lower)
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
            all_recipes=all_recipes,
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
            _invalidate_weekly_plan_save_state()
            _clear_grocery_session_overrides()
            _clear_grocery_result()
            st.rerun()

        all_names = sorted({recipe.name for recipe in all_recipes}, key=str.lower)

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
            all_recipes=all_recipes,
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


def _render_slot_manual_picker(
    *,
    slot_index: int,
    all_recipes: list,
    filter_columns: list[ColumnInfo],
    filter_defaults: MealPlanFilters,
    schema_columns: dict[str, ColumnInfo],
    ingredient_index: dict[str, set[str]],
) -> None:
    with st.expander("Choose recipe manually", expanded=False):
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

        def _dev_jump_button(
            target: DevJumpTarget,
            *,
            label: str,
            key_suffix: str,
            manual_recipes: list[str] | None,
        ) -> None:
            if not st.button(label, key=f"dev_jump_{target.value}_{key_suffix}"):
                return
            if manual_recipes is not None and not manual_recipes:
                st.warning("Pick at least one recipe for the manual meals jump.")
                return
            meal_count = int(st.session_state.get("plan_meal_count", DEFAULT_DEV_MEAL_COUNT))
            if manual_recipes is not None:
                names = list(manual_recipes)
            else:
                names = pick_default_recipe_names(
                    db.query_recipes(),
                    meal_count=meal_count,
                )
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
        _dev_jump_button(
            DevJumpTarget.MEALS_FILLED,
            label="Meals filled: auto",
            key_suffix="auto",
            manual_recipes=None,
        )
        manual_pick = st.multiselect(
            "Choose recipes manually",
            options=all_names,
            key="dev_jump_manual_recipes",
            placeholder="Pick one or more recipes…",
        )
        _dev_jump_button(
            DevJumpTarget.MEALS_FILLED,
            label="Meals filled: manual",
            key_suffix="manual",
            manual_recipes=manual_pick,
        )
        _dev_jump_button(
            DevJumpTarget.PRE_BUILD_GROCERY,
            label="Pre-build grocery",
            key_suffix="btn_pre_build",
            manual_recipes=None,
        )
        _dev_jump_button(
            DevJumpTarget.PER_RECIPE_REVIEW,
            label="Per-recipe review",
            key_suffix="btn_review",
            manual_recipes=None,
        )
        _dev_jump_button(
            DevJumpTarget.GROCERY_RESULT,
            label="Final list",
            key_suffix="btn_final_list",
            manual_recipes=None,
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
            _reset_weekly_plan_workflow(clear_mode=True)
            st.session_state.weekly_plan_mode_choice = "new"
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
                        return (
                            f"{plan.name} — w/o {plan.week_start.isoformat()} "
                            f"({len(plan.recipes)} meals)"
                        )
                return plan_name

            selected_plan_name = st.selectbox(
                "Saved plan",
                options,
                format_func=_saved_plan_label,
                key="weekly_plan_saved_name_pick",
            )

    if choice == "dev":
        st.session_state.weekly_plan_mode = "dev"
        _reset_weekly_plan_workflow(clear_mode=False)
        st.session_state.plan_meals_text = ""
        st.session_state.plan_meal_count = 1
        st.rerun()

    if st.button("Continue", type="primary", key="weekly_plan_mode_continue"):
        if choice == "saved" and not saved_plans:
            return False
        st.session_state.weekly_plan_mode = choice
        _reset_weekly_plan_workflow(clear_mode=False)
        if choice == "saved" and selected_plan_name:
            st.session_state.plan_meals_text = "\n".join(
                load_plan_recipes(selected_plan_name, recipes_db=get_db())
            )
            st.session_state.weekly_plan_loaded_name = selected_plan_name
        elif choice == "new":
            st.session_state.plan_meals_text = ""
            st.session_state.plan_meal_count = load_config().default_meals
        st.rerun()

    return False


def _ensure_plan_session_defaults() -> None:
    if "plan_meals_text" not in st.session_state:
        st.session_state.plan_meals_text = ""
    if _weekly_plan_mode() == "dev" and "plan_meal_count" not in st.session_state:
        st.session_state.plan_meal_count = 1


def _render_meal_count_input() -> int:
    config = load_config()
    st.markdown("### 1. Meals")
    if _weekly_plan_mode() == "dev":
        return int(
            st.number_input(
                "How many meals this week?",
                min_value=1,
                max_value=21,
                step=1,
                key="plan_meal_count",
            )
        )
    return int(
        st.number_input(
            "How many meals this week?",
            min_value=1,
            max_value=21,
            value=int(st.session_state.get("plan_meal_count", config.default_meals)),
            step=1,
            key="plan_meal_count",
        )
    )


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
) -> MealPlanFilters:
    schema = db.schema
    filter_defaults = default_filters(schema.all_columns)

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
        with st.spinner("Building your meal plan…"):
            locked_for_build = _locked_recipes_for_plan_build(meal_count=int(meal_count))
            plan = suggest_meals(
                all_recipes,
                meals=int(meal_count),
                locked_names=locked_for_build,
                filters=build_filters,
                schema_columns=schema.all_columns,
                ingredient_index=ingredient_index,
            )
            _write_plan_names(plan)
            st.session_state.plan_rejected_names = []
            _invalidate_weekly_plan_save_state()
            _clear_grocery_session_overrides()
            _clear_grocery_result()
            st.session_state.plan_last_week_filters = build_filters
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

    current_plan = _current_plan_names()
    if not current_plan:
        return

    def _apply_plan_swap(names_to_replace: list[str]) -> None:
        rejected = set(st.session_state.get("plan_rejected_names", []))
        new_plan, rejected = replace_meals_in_plan(
            current_plan,
            names_to_replace,
            all_recipes=all_recipes,
            pool=suggestion_pool,
            rejected_names=rejected,
        )
        _write_plan_names(new_plan)
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
    for index, name in enumerate(current_plan, start=1):
        meal_col, swap_col = st.columns([8, 1])
        with meal_col:
            st.markdown(
                f'<p class="gw-meal-slot-label">'
                f'<span class="gw-meal-slot-title">Meal {index}</span> — {html.escape(name)}</p>',
                unsafe_allow_html=True,
            )
            _render_slot_manual_picker(
                slot_index=index,
                all_recipes=all_recipes,
                filter_columns=filter_columns,
                filter_defaults=filter_defaults,
                schema_columns=schema.all_columns,
                ingredient_index=ingredient_index,
            )
        with swap_col:
            if st.button(
                "Swap",
                key=f"swap_meal_{index}",
                help="Pick a different recipe for this meal",
            ):
                _apply_plan_swap([name])

    if len(current_plan) < int(meal_count) and st.button(
        "Fill remaining slots", key="fill_remaining_plan"
    ):
        plan = suggest_meals(
            all_recipes,
            meals=int(meal_count),
            locked_names=current_plan,
            filters=week_filters,
            schema_columns=schema.all_columns,
            ingredient_index=ingredient_index,
        )
        _write_plan_names(plan)
        _invalidate_weekly_plan_save_state()
        _clear_grocery_session_overrides()
        _clear_grocery_result()
        st.rerun()

    if st.button("Re-generate all meals", key="regenerate_plan"):
        rejected = set(st.session_state.get("plan_rejected_names", []))
        plan = suggest_meals(
            all_recipes,
            meals=int(meal_count),
            locked_names=[],
            filters=week_filters,
            schema_columns=schema.all_columns,
            rejected_names=rejected,
            ingredient_index=ingredient_index,
        )
        _write_plan_names(plan)
        _invalidate_weekly_plan_save_state()
        _clear_grocery_session_overrides()
        _clear_grocery_result()
        st.rerun()

    _render_save_plan_controls(_current_plan_names(), cached_recipes=all_recipes)


def render_meals_section(db: NotionRecipesDB, *, all_recipes: list) -> list[str]:
    """Render step 1 (meals) and return the current planned recipe names."""
    _ensure_plan_session_defaults()
    meal_count = _render_meal_count_input()
    _render_dev_jump_tools(db)

    ingredient_index = _cached_plan_ingredient_index(all_recipes)
    current_plan = _current_plan_names()
    fallback_filters = default_filters(db.schema.all_columns)
    stored_filters = st.session_state.get("plan_last_week_filters", fallback_filters)

    if current_plan:
        _render_built_plan_meals(
            db,
            all_recipes=all_recipes,
            meal_count=meal_count,
            week_filters=stored_filters,
            ingredient_index=ingredient_index,
        )
        with st.expander("Adjust filters or rebuild plan", expanded=False):
            week_filters = _render_generate_plan_controls(
                db,
                all_recipes=all_recipes,
                meal_count=meal_count,
                ingredient_index=ingredient_index,
            )
            st.session_state.plan_last_week_filters = week_filters
    else:
        week_filters = _render_generate_plan_controls(
            db,
            all_recipes=all_recipes,
            meal_count=meal_count,
            ingredient_index=ingredient_index,
        )
        st.session_state.plan_last_week_filters = week_filters
        _render_built_plan_meals(
            db,
            all_recipes=all_recipes,
            meal_count=meal_count,
            week_filters=week_filters,
            ingredient_index=ingredient_index,
        )

    return _current_plan_names()
