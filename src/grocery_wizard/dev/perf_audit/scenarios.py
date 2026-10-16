"""Scenario catalogue: one entry per user-visible control or flow.

Add a scenario here whenever a new button, form, or page ships. ``covers`` lists the
Streamlit widget keys/labels the scenario exercises so the coverage check can flag
controls the audit does not measure yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from streamlit.testing.v1 import AppTest

from src.grocery_wizard.dev.perf_audit import flows
from src.grocery_wizard.dev.perf_audit.flows import AuditContext, ScenarioSkipError
from src.grocery_wizard.ui.ids import CONTROL_GLOBAL_REFRESH, control_streamlit_key

Prepare = Callable[[AuditContext], AppTest]
Act = Callable[[AuditContext, AppTest], AppTest]


@dataclass(frozen=True)
class Scenario:
    id: str
    page: str
    label: str
    prepare: Prepare
    act: Act
    covers: tuple[str, ...] = ()
    writes: bool = False
    external: bool = False
    note: str = ""


def _rerun(ctx: AuditContext, at: AppTest) -> AppTest:
    return at.run(timeout=ctx.timeout)


def _click(key: str | None = None, label: str | None = None) -> Act:
    def act(ctx: AuditContext, at: AppTest) -> AppTest:
        return flows.click(ctx, at, key=key, label=label)

    return act


def _page_open(slug: str) -> Scenario:
    def act(ctx: AuditContext, at: AppTest) -> AppTest:
        return flows.go_to_page(ctx, at, slug)

    return Scenario(
        id=f"global.page_switch.{slug}",
        page="global",
        label=f"Switch to the {slug} page",
        prepare=flows.open_app if slug != "weekly" else _open_other_page_then_back,
        act=act,
        covers=("page_picker",),
    )


def _open_other_page_then_back(ctx: AuditContext) -> AppTest:
    at = flows.open_app(ctx)
    flows.go_to_page(ctx, at, "pantry")
    return at


# --- global -----------------------------------------------------------------


def _app_load_prepare(ctx: AuditContext) -> AppTest:
    return flows.new_app(ctx)


def _app_load_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return at.run(timeout=ctx.timeout)


def _refresh_prepare(ctx: AuditContext) -> AppTest:
    return flows.open_app(ctx)


# --- weekly: start ------------------------------------------------------------


def _pick_saved_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.choose_start_mode(ctx, at, "saved")


def _pick_dev_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.choose_start_mode(ctx, at, "dev")


def _new_continue_prepare(ctx: AuditContext) -> AppTest:
    at = flows.open_app(ctx)
    return flows.choose_start_mode(ctx, at, "new")


# --- weekly: meals ----------------------------------------------------------------


def _quick_swap_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, key="swap_meal_1")


def _slot_use_recipe_prepare(ctx: AuditContext) -> AppTest:
    at = flows.start_new_plan_with_built_meals(ctx)
    picker = at.selectbox(key="plan_slot_direct_pick_1")
    if len(picker.options) < 2:
        raise ScenarioSkipError("Need at least two recipes to swap a slot")
    picker.set_value(picker.options[-1])
    return at.run(timeout=ctx.timeout)


def _slot_use_recipe_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, key="plan_slot_apply_direct_1")


def _prebuild_pin_prepare(ctx: AuditContext) -> AppTest:
    at = flows.start_new_plan_at_builder(ctx)
    picker = at.selectbox(key="plan_prebuild_direct_pick")
    if not picker.options:
        raise ScenarioSkipError("No recipes available to pin")
    picker.set_value(picker.options[0])
    return at.run(timeout=ctx.timeout)


def _save_plan_prepare(ctx: AuditContext) -> AppTest:
    return flows.start_new_plan_with_built_meals(ctx)


def _save_plan_act(ctx: AuditContext, at: AppTest) -> AppTest:
    labels = {b.key for b in at.button}
    if "weekly_plan_pick_next_week" in labels:
        flows.click(ctx, at, key="weekly_plan_pick_next_week")
    return flows.click(ctx, at, key="save_weekly_plan")


# --- weekly: grocery -----------------------------------------------------------------


def _grocery_ready_prepare(ctx: AuditContext) -> AppTest:
    return flows.dev_meals_ready_for_grocery(ctx)


def _review_prepare(ctx: AuditContext) -> AppTest:
    return flows.dev_jump(ctx, "per_recipe_review_btn_review")


def _build_final_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, label="Build final list")


def _review_cancel_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, key="review_cancel")


def _review_save_prepare(ctx: AuditContext) -> AppTest:
    at = flows.start_new_plan_with_built_meals(ctx)
    flows.click(ctx, at, key="save_weekly_plan")
    flows.click(ctx, at, key="create_grocery")
    if not at.text_area:
        raise ScenarioSkipError("Per-recipe review did not render")
    at.text_area[0].set_value(f"{at.text_area[0].value}\n1 perf-audit test item")
    return at.run(timeout=ctx.timeout)


def _review_save_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.button_with_prefix(at, "review_save_").click().run(timeout=ctx.timeout)


def _final_list_idle_prepare(ctx: AuditContext) -> AppTest:
    return flows.dev_jump(ctx, "grocery_result_btn_final_list")


def _rail_prepare(ctx: AuditContext) -> AppTest:
    return flows.dev_jump(ctx, "meals_filled_auto")


# --- add recipe ----------------------------------------------------------------------


def _add_prepare(ctx: AuditContext) -> AppTest:
    return flows.open_page(ctx, "add")


def _add_duplicate_prepare(ctx: AuditContext) -> AppTest:
    link = flows.first_recipe_link(ctx)
    at = flows.open_page(ctx, "add")
    at.text_area(key="add_recipe_urls").set_value(link)
    return at.run(timeout=ctx.timeout)


def _add_manual_save_prepare(ctx: AuditContext) -> AppTest:
    at = flows.open_page(ctx, "add")
    flows.click(ctx, at, key="add_recipe_manual_start")
    name_inputs = [t for t in at.text_input if t.label == "Name"]
    ingredient_areas = [t for t in at.text_area if t.label == "Ingredients"]
    if not name_inputs or not ingredient_areas:
        raise ScenarioSkipError("Manual recipe editor fields not found")
    name_inputs[0].set_value("Perf audit test recipe")
    ingredient_areas[0].set_value("1 cup water")
    return at.run(timeout=ctx.timeout)


# --- pantry --------------------------------------------------------------------------


def _pantry_prepare(ctx: AuditContext) -> AppTest:
    return flows.open_page(ctx, "pantry")


def _pantry_search_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return at.text_input(key="pantry_staples_search").set_value("salt").run(timeout=ctx.timeout)


def _pantry_add_prepare(ctx: AuditContext) -> AppTest:
    at = flows.open_page(ctx, "pantry")
    boxes = [t for t in at.text_input if t.label == "Add pantry item"]
    if not boxes:
        raise ScenarioSkipError("Add pantry item input not found")
    boxes[0].set_value("perf audit test item")
    return at.run(timeout=ctx.timeout)


def _pantry_add_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, label="Add to pantry")


def _pantry_remove_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.button_with_prefix(at, "pantry_rm_").click().run(timeout=ctx.timeout)


def _recurring_add_prepare(ctx: AuditContext) -> AppTest:
    at = flows.open_page(ctx, "pantry")
    boxes = [t for t in at.text_input if t.label == "Add recurring item"]
    if not boxes:
        raise ScenarioSkipError("Add recurring item input not found")
    boxes[0].set_value("perf audit test recurring")
    return at.run(timeout=ctx.timeout)


def _recurring_add_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, label="Add recurring item")


def _recurring_remove_act(ctx: AuditContext, at: AppTest) -> AppTest:
    picks = [s for s in at.selectbox if s.key == "pantry_recurring_remove_pick"]
    if not picks or len(picks[0].options) < 2:
        raise ScenarioSkipError("No recurring items to remove")
    picks[0].set_value(picks[0].options[1])
    return flows.click(ctx, at, label="Remove selected")


# --- maintenance ---------------------------------------------------------------------


def _maintenance_prepare(ctx: AuditContext) -> AppTest:
    return flows.open_page(ctx, "maintenance")


def _maintenance_pick_recipe_act(ctx: AuditContext, at: AppTest) -> AppTest:
    picker = at.selectbox(key="recipe_maint_meal_plan_status_recipe")
    if len(picker.options) < 2:
        raise ScenarioSkipError("Need at least two recipes")
    return picker.set_value(picker.options[1]).run(timeout=ctx.timeout)


def _maintenance_status_prepare(ctx: AuditContext) -> AppTest:
    at = flows.open_page(ctx, "maintenance")
    selects = [s for s in at.selectbox if s.label == "Meal plan status"]
    if not selects:
        raise ScenarioSkipError("Meal plan status editor unavailable")
    current = selects[0].value
    other = next((o for o in selects[0].options if o != current), None)
    if other is None:
        raise ScenarioSkipError("Only one status option")
    selects[0].set_value(other)
    return at.run(timeout=ctx.timeout)


def _maintenance_status_act(ctx: AuditContext, at: AppTest) -> AppTest:
    return flows.click(ctx, at, label="Apply meal plan status")


def _external_unsupported_act(ctx: AuditContext, at: AppTest) -> AppTest:
    raise ScenarioSkipError(
        "Calls an external service (NYT, GitHub, recipe sites); time it by hand in the browser"
    )


def build_scenarios() -> list[Scenario]:
    refresh_key = control_streamlit_key(CONTROL_GLOBAL_REFRESH)
    return [
        # global
        Scenario(
            "global.app_load",
            "global",
            "First page load of the app",
            _app_load_prepare,
            _app_load_act,
        ),
        Scenario(
            "global.refresh",
            "global",
            "Refresh from Notion",
            _refresh_prepare,
            _click(key=refresh_key),
            covers=(refresh_key,),
        ),
        _page_open("weekly"),
        _page_open("add"),
        _page_open("pantry"),
        _page_open("maintenance"),
        Scenario(
            "global.feedback.submit",
            "global",
            "Send feedback (submit)",
            flows.open_app,
            _external_unsupported_act,
            covers=("gw_feedback_submit",),
            external=True,
        ),
        # weekly: start
        Scenario(
            "weekly.start.pick_saved",
            "weekly",
            "Choose 'Continue a saved plan'",
            flows.open_app,
            _pick_saved_act,
            covers=("weekly_plan_mode_choice",),
        ),
        Scenario(
            "weekly.start.pick_dev",
            "weekly",
            "Choose Dev mode",
            flows.open_app,
            _pick_dev_act,
        ),
        Scenario(
            "weekly.start.continue_new",
            "weekly",
            "Continue (new plan)",
            _new_continue_prepare,
            _click(key="weekly_plan_mode_continue"),
            covers=("weekly_plan_mode_continue",),
        ),
        Scenario(
            "weekly.start.continue_saved",
            "weekly",
            "Continue (saved plan) to meals",
            flows.pick_saved_plan,
            _click(key="weekly_plan_mode_continue"),
        ),
        # weekly: meals
        Scenario(
            "weekly.meals.count_continue",
            "weekly",
            "Continue after meal count (opens builder)",
            flows.start_new_plan_at_meal_count,
            _click(key="weekly_plan_meal_count_continue"),
            covers=("weekly_plan_meal_count_continue",),
        ),
        Scenario(
            "weekly.meals.build_plan",
            "weekly",
            "Build my plan",
            flows.start_new_plan_at_builder,
            _click(key="build_plan"),
            covers=("build_plan",),
        ),
        Scenario(
            "weekly.meals.quick_swap",
            "weekly",
            "Quick swap one meal",
            flows.start_new_plan_with_built_meals,
            _quick_swap_act,
            covers=("swap_meal_",),
            writes=True,
        ),
        Scenario(
            "weekly.meals.regenerate_all",
            "weekly",
            "Re-generate all meals",
            flows.start_new_plan_with_built_meals,
            _click(key="regenerate_plan"),
            covers=("regenerate_plan",),
            writes=True,
        ),
        Scenario(
            "weekly.meals.slot_use_recipe",
            "weekly",
            "Choose manually: use this recipe",
            _slot_use_recipe_prepare,
            _slot_use_recipe_act,
            covers=("plan_slot_apply_direct_", "plan_slot_apply_"),
        ),
        Scenario(
            "weekly.meals.prebuild_pin",
            "weekly",
            "Pin a recipe before building",
            _prebuild_pin_prepare,
            _click(key="plan_prebuild_pin_direct"),
            covers=("plan_prebuild_pin_direct", "plan_prebuild_pin_recipe", "plan_prebuild_unpin_"),
        ),
        Scenario(
            "weekly.meals.idle_rerun_new",
            "weekly",
            "Idle rerun with a built (new) plan",
            flows.start_new_plan_with_built_meals,
            _rerun,
        ),
        Scenario(
            "weekly.meals.idle_rerun_saved",
            "weekly",
            "Idle rerun with a loaded saved plan",
            flows.start_saved_plan_at_meals,
            _rerun,
        ),
        Scenario(
            "weekly.meals.save_plan",
            "weekly",
            "Save plan to Notion",
            _save_plan_prepare,
            _save_plan_act,
            covers=("save_weekly_plan", "weekly_plan_pick_this_week", "weekly_plan_pick_next_week"),
            writes=True,
        ),
        Scenario(
            "weekly.meals.dev_continue",
            "weekly",
            "Dev: continue to grocery list",
            lambda ctx: flows.dev_jump(ctx, "meals_filled_auto"),
            _click(key="dev_continue_to_grocery"),
            covers=("dev_continue_to_grocery",),
        ),
        Scenario(
            "weekly.rail.grocery_step",
            "weekly",
            "Open the Grocery list step from the rail",
            _rail_prepare,
            _click(key="weekly_rail_grocery_list"),
            covers=("weekly_rail_", "weekly_plan_change_mode"),
        ),
        # weekly: grocery
        Scenario(
            "weekly.grocery.create_list_dev",
            "weekly",
            "Create grocery list (dev, no save)",
            _grocery_ready_prepare,
            _click(key="create_grocery"),
            covers=("create_grocery",),
        ),
        Scenario(
            "weekly.grocery.build_final",
            "weekly",
            "Build final list",
            _review_prepare,
            _build_final_act,
            covers=("Build final list",),
        ),
        Scenario(
            "weekly.grocery.final_list_idle",
            "weekly",
            "Idle rerun on the final list",
            _final_list_idle_prepare,
            _rerun,
        ),
        Scenario(
            "weekly.grocery.review_cancel",
            "weekly",
            "Cancel review",
            _review_prepare,
            _review_cancel_act,
            covers=("review_cancel",),
        ),
        Scenario(
            "weekly.grocery.review_save_recipe",
            "weekly",
            "Review: save one recipe to Notion",
            _review_save_prepare,
            _review_save_act,
            covers=("review_save_",),
            writes=True,
        ),
        # add recipe
        Scenario(
            "add.url.empty",
            "add",
            "Add recipe with empty URL",
            _add_prepare,
            _click(key="add_recipe_from_url"),
            covers=("add_recipe_from_url",),
        ),
        Scenario(
            "add.url.duplicate",
            "add",
            "Add recipe from a URL already in Notion",
            _add_duplicate_prepare,
            _click(key="add_recipe_from_url"),
        ),
        Scenario(
            "add.manual.start_blank",
            "add",
            "Start blank recipe",
            _add_prepare,
            _click(key="add_recipe_manual_start"),
            covers=("add_recipe_manual_start",),
        ),
        Scenario(
            "add.manual.save",
            "add",
            "Save manual recipe to Notion",
            _add_manual_save_prepare,
            _click(key="save_0"),
            covers=("save_",),
            writes=True,
        ),
        Scenario(
            "add.nyt.sync",
            "add",
            "NYT: refresh folders / sync",
            _add_prepare,
            _external_unsupported_act,
            covers=("nyt_sync_run", "nyt_sync_refresh_folders", "nyt_sync_retry_auth"),
            external=True,
        ),
        # pantry
        Scenario(
            "pantry.search",
            "pantry",
            "Type in pantry search",
            _pantry_prepare,
            _pantry_search_act,
        ),
        Scenario(
            "pantry.add_item",
            "pantry",
            "Add pantry item",
            _pantry_add_prepare,
            _pantry_add_act,
            covers=("Add to pantry",),
            writes=True,
        ),
        Scenario(
            "pantry.remove_item",
            "pantry",
            "Remove pantry item (x)",
            _pantry_prepare,
            _pantry_remove_act,
            covers=("pantry_rm_",),
            writes=True,
        ),
        Scenario(
            "pantry.add_recurring",
            "pantry",
            "Add recurring item",
            _recurring_add_prepare,
            _recurring_add_act,
            covers=("Add recurring item",),
            writes=True,
        ),
        Scenario(
            "pantry.remove_recurring",
            "pantry",
            "Remove recurring item",
            _pantry_prepare,
            _recurring_remove_act,
            covers=("Remove selected",),
            writes=True,
        ),
        # maintenance
        Scenario(
            "maintenance.pick_recipe",
            "maintenance",
            "Pick a recipe for status",
            _maintenance_prepare,
            _maintenance_pick_recipe_act,
        ),
        Scenario(
            "maintenance.apply_status",
            "maintenance",
            "Apply meal plan status",
            _maintenance_status_prepare,
            _maintenance_status_act,
            covers=("meal_plan_status_apply_",),
            writes=True,
        ),
        Scenario(
            "maintenance.backfill_ingredients",
            "maintenance",
            "Start ingredients backfill",
            _maintenance_prepare,
            _external_unsupported_act,
            covers=("recipe_maint_ingredients",),
            writes=True,
            external=True,
        ),
        Scenario(
            "maintenance.backfill_metadata",
            "maintenance",
            "Start metadata backfill",
            _maintenance_prepare,
            _external_unsupported_act,
            covers=("recipe_maint_metadata",),
            writes=True,
            external=True,
        ),
    ]
