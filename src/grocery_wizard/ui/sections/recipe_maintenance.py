"""Recipe maintenance tab — batch backfill for Notion recipe rows."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.grocery_wizard.integrations.notion_views import (
    ensure_manual_ingredients_notion_view_url,
    ensure_possibly_missing_checkboxes_notion_view_url,
)
from src.grocery_wizard.integrations.nyt_cooking import NYTCookingClient, credentials_status
from src.grocery_wizard.recipes.recipe_maintenance import (
    BackfillSummary,
    FractionCallback,
    ProgressCallback,
    format_backfill_summary,
    recipes_manual_ingredients_in_notion,
    recipes_missing_ingredients,
    recipes_missing_metadata,
    recipes_possibly_missing_all_checkboxes,
    run_ingredients_backfill,
    run_metadata_backfill,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import cached_query_recipes, invalidate_notion_cache

_MANUAL_INGREDIENTS_CHECKBOX_KEY = "recipe_maint_notion_manual_ingredients"
_MANUAL_CHECKBOXES_CHECKBOX_KEY = "recipe_maint_notion_manual_checkboxes"
_OPEN_PENDING_KEYS = {
    _MANUAL_INGREDIENTS_CHECKBOX_KEY: "gw_manual_notion_open_pending_ingredients",
    _MANUAL_CHECKBOXES_CHECKBOX_KEY: "gw_manual_notion_open_pending_checkboxes",
}


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


def _queue_notion_open(*, checkbox_key: str) -> None:
    pending_key = _OPEN_PENDING_KEYS[checkbox_key]
    st.session_state[pending_key] = True


def _render_notion_open_control(
    *,
    checkbox_key: str,
    checkbox_label: str,
    url: str,
) -> None:
    st.checkbox(
        checkbox_label,
        key=checkbox_key,
        on_change=_queue_notion_open,
        kwargs={"checkbox_key": checkbox_key},
    )
    if not st.session_state.get(checkbox_key):
        return

    st.link_button(
        "Open filtered recipe database in Notion",
        url,
        type="secondary",
        use_container_width=True,
    )
    pending_key = _OPEN_PENDING_KEYS[checkbox_key]
    if st.session_state.pop(pending_key, False):
        st.components.v1.html(
            f"<script>window.open({url!r}, '_blank', 'noopener,noreferrer');</script>",
            height=0,
            width=0,
        )


def _preview_count_line(count: int) -> None:
    st.write(f"**{count}** recipe(s) will appear in Notion with this filter.")


def render_recipe_maintenance() -> None:
    st.caption(
        "Housekeeping for recipes already in Notion — fill missing ingredients or metadata "
        "from recipe links without using **Add Recipe**."
    )

    db = get_db()
    schema = db.schema
    recipes = cached_query_recipes(db)

    missing_ingredients = recipes_missing_ingredients(recipes, schema)
    missing_metadata = recipes_missing_metadata(recipes, schema)
    manual_ingredients = recipes_manual_ingredients_in_notion(recipes, schema)
    possibly_missing_checkboxes = recipes_possibly_missing_all_checkboxes(recipes, schema)
    checkbox_names = [col.name for col in schema.checkbox_columns]

    st.markdown("### Automatic backfill")

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
        st.markdown("**Backfill missing metadata**")
        st.caption(
            "Fills empty Meal, Cuisine, and meal-appropriate filters (e.g. Dinner Category "
            "only when Meal is Dinner; Weeknight Friendly for dinners). Instructions, NYT "
            "sync, and Showstopper are not auto-filled."
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

    st.markdown("### Manual backfill in Notion")
    st.caption("Open a filtered database view to edit rows yourself.")

    with st.container(border=True):
        st.markdown("**Write ingredients in Notion**")
        st.caption(
            "Filter: **Link** is empty and **Ingredients** is empty — rows we cannot "
            "auto-backfill; add URLs and ingredient lists by hand in Notion."
        )
        if not schema.ingredients_column:
            st.info("This Notion database has no Ingredients column configured.")
        else:
            _preview_count_line(len(manual_ingredients))
            try:
                ingredients_view_url = ensure_manual_ingredients_notion_view_url(db)
            except Exception as exc:
                st.error(f"Could not prepare Notion view: {exc}")
            else:
                _render_notion_open_control(
                    checkbox_key=_MANUAL_INGREDIENTS_CHECKBOX_KEY,
                    checkbox_label="Open Notion with this filter (new tab)",
                    url=ingredients_view_url,
                )

    with st.container(border=True):
        st.markdown("**Review checkbox columns in Notion**")
        if not checkbox_names:
            st.info("This Notion database has no checkbox review columns.")
        else:
            joined = ", ".join(f"**{name}**" for name in checkbox_names)
            st.caption(
                f"Filter: all of {joined} are unchecked. These may be missing metadata "
                "or intentionally left off — review and check boxes only where appropriate."
            )
            _preview_count_line(len(possibly_missing_checkboxes))
            try:
                checkboxes_view_url = ensure_possibly_missing_checkboxes_notion_view_url(db)
            except Exception as exc:
                st.error(f"Could not prepare Notion view: {exc}")
            else:
                _render_notion_open_control(
                    checkbox_key=_MANUAL_CHECKBOXES_CHECKBOX_KEY,
                    checkbox_label="Open Notion with this filter (new tab)",
                    url=checkboxes_view_url,
                )
