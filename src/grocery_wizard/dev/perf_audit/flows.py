"""Headless AppTest helpers that walk the Streamlit app to a given state."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from streamlit.testing.v1 import AppTest

from src.grocery_wizard.ui.ids import CONTROL_GLOBAL_PAGE_PICKER, control_streamlit_key
from src.grocery_wizard.ui.views import page_label_for_slug

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "app.py")
_PAGE_PICKER_KEY = control_streamlit_key(CONTROL_GLOBAL_PAGE_PICKER)
_RENDER_SLUG_KEY = "gw_render_page_slug"


class ScenarioSkipError(Exception):
    """Raised by a scenario when its precondition is not met (for example, no saved plans)."""


@dataclass
class AuditContext:
    """Shared per-audit settings and lazily discovered Notion facts."""

    timeout: int = 180
    facts: dict[str, Any] = field(default_factory=dict)


def new_app(ctx: AuditContext) -> AppTest:
    os.environ.setdefault("GROCERY_WIZARD_DEV_UI", "1")
    return AppTest.from_file(os.path.abspath(APP_PATH), default_timeout=ctx.timeout)


def open_app(ctx: AuditContext) -> AppTest:
    at = new_app(ctx)
    at.run(timeout=ctx.timeout)
    return at


def go_to_page(ctx: AuditContext, at: AppTest, slug: str) -> AppTest:
    label = page_label_for_slug(slug)
    if label is None:
        raise ScenarioSkipError(f"Unknown page slug {slug}")
    at.session_state[_PAGE_PICKER_KEY] = label
    at.session_state[_RENDER_SLUG_KEY] = slug
    return at.run(timeout=ctx.timeout)


def open_page(ctx: AuditContext, slug: str) -> AppTest:
    """Fresh app, then switch to ``slug`` (the switch is part of setup, not measured)."""
    at = open_app(ctx)
    if slug != "weekly":
        go_to_page(ctx, at, slug)
    return at


def button(at: AppTest, *, key: str | None = None, label: str | None = None) -> Any:
    for candidate in at.button:
        if key is not None and candidate.key == key:
            return candidate
        if label is not None and candidate.label == label:
            return candidate
    wanted = key or label
    raise ScenarioSkipError(f"Button {wanted!r} not found on the page")


def button_with_prefix(at: AppTest, prefix: str) -> Any:
    for candidate in at.button:
        if (candidate.key or "").startswith(prefix):
            return candidate
    raise ScenarioSkipError(f"No button with key prefix {prefix!r}")


def click(
    ctx: AuditContext, at: AppTest, *, key: str | None = None, label: str | None = None
) -> AppTest:
    return button(at, key=key, label=label).click().run(timeout=ctx.timeout)


def choose_start_mode(ctx: AuditContext, at: AppTest, mode: str) -> AppTest:
    radio = at.radio(key="weekly_plan_mode_choice")
    return radio.set_value(mode).run(timeout=ctx.timeout)


def start_new_plan_at_meal_count(ctx: AuditContext, at: AppTest | None = None) -> AppTest:
    app = at or open_app(ctx)
    choose_start_mode(ctx, app, "new")
    return click(ctx, app, key="weekly_plan_mode_continue")


def start_new_plan_at_builder(ctx: AuditContext) -> AppTest:
    app = start_new_plan_at_meal_count(ctx)
    return click(ctx, app, key="weekly_plan_meal_count_continue")


def start_new_plan_with_built_meals(ctx: AuditContext) -> AppTest:
    app = start_new_plan_at_builder(ctx)
    return click(ctx, app, key="build_plan")


def pick_saved_plan(ctx: AuditContext, at: AppTest | None = None) -> AppTest:
    app = at or open_app(ctx)
    choose_start_mode(ctx, app, "saved")
    if not app.selectbox(key="weekly_plan_saved_name_pick").options:
        raise ScenarioSkipError("No saved weekly plans in Notion")
    return app


def start_saved_plan_at_meals(ctx: AuditContext) -> AppTest:
    app = pick_saved_plan(ctx)
    return click(ctx, app, key="weekly_plan_mode_continue")


def start_dev_mode_at_builder(ctx: AuditContext) -> AppTest:
    app = open_app(ctx)
    choose_start_mode(ctx, app, "dev")
    return click(ctx, app, key="weekly_plan_meal_count_continue")


def dev_jump(ctx: AuditContext, key_suffix: str) -> AppTest:
    """Dev mode → one of the dev-tools jump buttons (``meals_filled_auto`` etc.)."""
    app = start_dev_mode_at_builder(ctx)
    return click(ctx, app, key=f"dev_jump_{key_suffix}")


def dev_meals_ready_for_grocery(ctx: AuditContext) -> AppTest:
    app = dev_jump(ctx, "meals_filled_auto")
    return click(ctx, app, key="dev_continue_to_grocery")


def first_recipe_link(ctx: AuditContext) -> str:
    """A recipe URL already in Notion, so the Add-recipe duplicate path is read-only."""
    if "recipe_link" not in ctx.facts:
        from src.grocery_wizard.ui.db_access import get_db

        recipes = get_db().query_recipes()
        link = next((r.link for r in recipes if r.link), None)
        ctx.facts["recipe_link"] = link
    link = ctx.facts["recipe_link"]
    if not link:
        raise ScenarioSkipError("No recipe with a Link in Notion")
    return str(link)
