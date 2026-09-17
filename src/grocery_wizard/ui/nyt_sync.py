"""Streamlit controls for syncing NYT Cooking recipe box to Notion."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.integrations.nyt_cooking import (
    NytAuthError,
    NYTCookingClient,
    NYTCookingError,
    NytRecipeBoxFolder,
    credentials_status,
    format_metadata_review,
    format_sync_summary,
    list_recipe_box_folders,
    load_sync_report,
    run_recipe_box_sync,
    verify_nyt_credentials,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import invalidate_notion_cache


def _folder_option_label(folder: NytRecipeBoxFolder) -> str:
    if folder.recipe_count is None:
        return folder.label
    return f"{folder.label} ({folder.recipe_count} recipes)"


@st.cache_data(show_spinner=False, ttl=300)
def _cached_recipe_box_folders() -> list[NytRecipeBoxFolder]:
    client = NYTCookingClient()
    verify_nyt_credentials(client)
    return list_recipe_box_folders(client)


def _render_nyt_credentials_panel() -> bool:
    """Warn when NYT env vars are missing. Returns True when configured."""
    status = credentials_status()
    if status["configured"]:
        return True
    st.warning(
        "NYT credentials are not set. Add `NYT_S_COOKIE` and `NYT_REGI_ID` "
        "(or `NYT_USER_ID`) to your environment — see the package README."
    )
    return False


def _load_nyt_recipe_box_folders() -> list[NytRecipeBoxFolder] | None:
    try:
        return _cached_recipe_box_folders()
    except NytAuthError as exc:
        st.error(str(exc))
        if st.button("Retry NYT connection", key="nyt_sync_retry_auth"):
            _cached_recipe_box_folders.clear()
            st.rerun()
        return None
    except NYTCookingError as exc:
        st.error(f"Could not load NYT recipe box: {exc}")
        return None


def _render_nyt_folder_picker(folders: list[NytRecipeBoxFolder]) -> NytRecipeBoxFolder:
    labels = [_folder_option_label(folder) for folder in folders]
    picked_label = st.selectbox(
        "Recipe-box folder",
        labels,
        key="nyt_sync_folder",
    )
    picked_index = labels.index(picked_label)
    return folders[picked_index]


def _render_nyt_sync_actions() -> tuple[bool, bool]:
    """Dry-run toggle, last-sync popover, refresh/run buttons."""
    dry_run = st.checkbox(
        "Dry run (preview only — no Notion writes)",
        value=False,
        key="nyt_sync_dry_run",
    )

    last_report = load_sync_report()
    if last_report is not None:
        with st.popover("Last sync metadata review"):
            st.text(format_metadata_review(last_report))

    run_col, refresh_col = st.columns(2)
    with refresh_col:
        if st.button(
            "Refresh folders",
            key="nyt_sync_refresh_folders",
            use_container_width=True,
        ):
            _cached_recipe_box_folders.clear()
            st.rerun()

    with run_col:
        run_clicked = st.button(
            "Preview sync" if dry_run else "Sync to Notion",
            key="nyt_sync_run",
            type="primary",
            use_container_width=True,
        )

    return run_clicked, dry_run


def _execute_nyt_recipe_box_sync(
    *,
    folder: NytRecipeBoxFolder,
    dry_run: bool,
) -> None:
    progress_lines: list[str] = []

    def on_progress(message: str) -> None:
        progress_lines.append(message)

    db = get_db()
    client = NYTCookingClient()

    with st.status(
        "Previewing NYT recipes…" if dry_run else "Syncing NYT recipes to Notion…",
        expanded=True,
    ) as sync_status:
        try:
            result = run_recipe_box_sync(
                db,
                client,
                collection_id=folder.collection_id,
                collection_label=folder.label,
                dry_run=dry_run,
                on_progress=on_progress,
            )
        except NytAuthError as exc:
            sync_status.update(label="NYT sync failed", state="error")
            st.error(str(exc))
            return
        except NYTCookingError as exc:
            sync_status.update(label="NYT sync failed", state="error")
            st.error(str(exc))
            return

        for line in progress_lines:
            st.write(line)

        summary = result.summary
        sync_status.update(
            label=format_sync_summary(summary),
            state="complete",
        )

    if dry_run:
        st.info("Dry run — no recipes were written to Notion.")
    elif summary.created:
        invalidate_notion_cache()
        st.success(f"Added {summary.created} recipe(s) to Notion.")

    if result.review_report:
        with st.expander("Metadata review", expanded=bool(result.review_report.get("created"))):
            st.text(format_metadata_review(result.review_report))
        flagged = sum(
            1 for recipe in result.review_report.get("created", []) if recipe.get("flags")
        )
        if flagged and not dry_run:
            st.caption(
                f"{flagged} recipe(s) flagged — review metadata in Notion or expand "
                "Metadata review above."
            )


def render_nyt_sync_controls() -> None:
    """Sidebar-adjacent NYT recipe-box sync (folder picker, dry run, sync)."""
    with st.expander("Sync from NYT Cooking", expanded=False):
        if not _render_nyt_credentials_panel():
            return

        folders = _load_nyt_recipe_box_folders()
        if folders is None:
            return

        folder = _render_nyt_folder_picker(folders)
        run_clicked, dry_run = _render_nyt_sync_actions()
        if not run_clicked:
            return

        _execute_nyt_recipe_box_sync(folder=folder, dry_run=dry_run)
