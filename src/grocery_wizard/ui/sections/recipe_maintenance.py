"""Recipe maintenance tab — batch backfill for Notion recipe rows."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.grocery_wizard.integrations.notion_views import ensure_manual_backfill_notion_view_url
from src.grocery_wizard.integrations.nyt_cooking import NYTCookingClient, credentials_status
from src.grocery_wizard.recipes.recipe_maintenance import (
    BackfillSummary,
    FractionCallback,
    ProgressCallback,
    format_backfill_summary,
    recipes_manual_notion_backfill,
    recipes_missing_ingredients,
    recipes_missing_metadata,
    run_ingredients_backfill,
    run_metadata_backfill,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, invalidate_notion_cache

_MANUAL_NOTION_CHECKBOX_KEY = "recipe_maint_notion_manual"
_MANUAL_NOTION_OPEN_PENDING_KEY = "gw_manual_notion_open_pending"


def _nyt_client_if_configured() -> NYTCookingClient | None:
    if not credentials_status()["configured"]:
        return None
    return NYTCookingClient()


def _run_backfill_with_progress(
    *,
    label: str,
    runner: Callable[..., BackfillSummary],
) -> None:
    progress_lines: list[str] = []
    progress_bar = st.progress(0.0, text=f"{label}…")

    def on_progress(message: str) -> None:
        progress_lines.append(message)

    def on_fraction(fraction: float) -> None:
        progress_bar.progress(min(max(fraction, 0.0), 1.0), text=f"{label}…")

    with st.status(label, expanded=True) as status:
        summary = runner(on_progress=on_progress, on_fraction=on_fraction)
        for line in progress_lines[-40:]:
            st.write(line)
        outcome = format_backfill_summary(label, summary)
        status.update(label=outcome, state="complete")

    progress_bar.progress(1.0, text=outcome)
    st.success(outcome)
    if summary.succeeded:
        invalidate_notion_cache()


def _queue_manual_notion_open() -> None:
    st.session_state[_MANUAL_NOTION_OPEN_PENDING_KEY] = True


def _render_manual_notion_open(*, url: str) -> None:
    st.link_button(
        "Open filtered recipe database in Notion",
        url,
        type="secondary",
        use_container_width=True,
    )
    if st.session_state.pop(_MANUAL_NOTION_OPEN_PENDING_KEY, False):
        st.components.v1.html(
            f"<script>window.open({url!r}, '_blank', 'noopener,noreferrer');</script>",
            height=0,
            width=0,
        )


def render_recipe_maintenance() -> None:
    st.caption(
        "Housekeeping for recipes already in Notion — fill missing ingredients or metadata "
        "from recipe links without using **Add Recipe**."
    )

    db = get_db()
    schema = db.schema
    recipes = cached_query_recipes(db)

    missing_ingredients = recipes_missing_ingredients(recipes, schema)
    manual_notion = recipes_manual_notion_backfill(recipes, schema)
    missing_metadata = recipes_missing_metadata(recipes, schema)

    with st.container(border=True):
        st.markdown("**Backfill missing ingredients**")
        st.caption("Recipes with a link but empty Ingredients column.")
        if not schema.ingredients_column:
            st.info("This Notion database has no Ingredients column configured.")
        else:
            st.write(f"**{len(missing_ingredients)}** recipe(s) missing ingredients.")
            if st.button(
                "Start ingredients backfill",
                type="primary",
                key="recipe_maint_ingredients",
                disabled=not missing_ingredients,
            ):

                def _ingredients_runner(
                    *,
                    on_progress: ProgressCallback | None = None,
                    on_fraction: FractionCallback | None = None,
                ) -> BackfillSummary:
                    return run_ingredients_backfill(
                        db,
                        missing_ingredients,
                        on_progress=on_progress,
                        on_fraction=on_fraction,
                    )

                _run_backfill_with_progress(
                    label="Ingredients backfill",
                    runner=_ingredients_runner,
                )

    with st.container(border=True):
        st.markdown("**Manual backfill in Notion**")
        st.caption(
            "Opens your recipe database with filters **Link is empty** and "
            "**Ingredients is empty** so you can add URLs and ingredient lists by hand."
        )
        st.write(f"**{len(manual_notion)}** recipe(s) match this filter.")
        try:
            manual_notion_url = ensure_manual_backfill_notion_view_url(db)
        except Exception as exc:
            st.error(f"Could not prepare Notion view: {exc}")
        else:
            st.checkbox(
                "Open Notion with this filter (new tab)",
                key=_MANUAL_NOTION_CHECKBOX_KEY,
                on_change=_queue_manual_notion_open,
            )
            if st.session_state.get(_MANUAL_NOTION_CHECKBOX_KEY):
                _render_manual_notion_open(url=manual_notion_url)

    with st.container(border=True):
        st.markdown("**Backfill missing metadata**")
        st.caption(
            "Recipes with ingredients but empty Meal / filter columns — filled from "
            "classification (checkboxes and Instructions are not changed here)."
        )
        st.write(f"**{len(missing_metadata)}** recipe(s) with gaps in metadata columns.")
        if st.button(
            "Start metadata backfill",
            type="primary",
            key="recipe_maint_metadata",
            disabled=not missing_metadata,
        ):
            nyt_client = _nyt_client_if_configured()

            def _metadata_runner(
                *,
                on_progress: ProgressCallback | None = None,
                on_fraction: FractionCallback | None = None,
            ) -> BackfillSummary:
                return run_metadata_backfill(
                    db,
                    missing_metadata,
                    nyt_client=nyt_client,
                    on_progress=on_progress,
                    on_fraction=on_fraction,
                )

            _run_backfill_with_progress(label="Metadata backfill", runner=_metadata_runner)
