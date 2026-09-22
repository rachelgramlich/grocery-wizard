"""Add-recipe tab."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.ingredients.sync import prepare_ingredients_for_notion
from src.grocery_wizard.integrations.notion import (
    DatabaseSchema,
    NotionFieldValues,
    NotionRecipesDB,
)
from src.grocery_wizard.recipes.add_recipe import (
    RecipeUrlPreview,
    base_recipe_field_values,
    ordered_recipe_field_names,
    preview_recipe_urls,
)
from src.grocery_wizard.ui.db_access import get_db
from src.grocery_wizard.ui.notion_cache import invalidate_notion_cache
from src.grocery_wizard.ui.nyt_sync import render_nyt_sync_controls

_ENTRY_PATH_URL = "url"
_ENTRY_PATH_MANUAL = "manual"
_ENTRY_PATH_NYT = "nyt"
_MANUAL_RECIPE_EPOCH_KEY = "add_recipe_manual_epoch"


def render_add_recipe() -> None:
    st.caption("Choose one of three ways to add recipes to Notion.")

    db = get_db()
    schema = db.schema
    previews = st.session_state.get("preview_recipes", [])

    with st.container(border=True):
        st.markdown("**Recipe URL**")
        st.caption("Paste a link to pull in name and ingredients, then save to Notion.")
        urls_text = st.text_area(
            "Recipe URL",
            placeholder="https://example.com/my-recipe",
            height=80,
            key="add_recipe_urls",
        )
        if st.button("Add recipe", type="primary", key="add_recipe_from_url"):
            urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
            if not urls:
                st.warning("Paste a recipe URL first.")
            else:
                st.session_state["preview_recipes"] = _previews_for_ui(db, urls)
                previews = st.session_state["preview_recipes"]
        _render_previews_for_entry(db, schema, previews, _ENTRY_PATH_URL)

    with st.container(border=True):
        st.markdown("**Type it in myself**")
        st.caption("Start from a blank recipe and fill in the details.")
        if st.button(
            "Start blank recipe",
            type="primary",
            key="add_recipe_manual_start",
        ):
            st.session_state[_MANUAL_RECIPE_EPOCH_KEY] = (
                int(st.session_state.get(_MANUAL_RECIPE_EPOCH_KEY, 0)) + 1
            )
            st.session_state["preview_recipes"] = [
                _preview_dict(
                    RecipeUrlPreview(
                        status="manual",
                        url="",
                        fields=base_recipe_field_values(schema),
                    ),
                    entry_path=_ENTRY_PATH_MANUAL,
                )
            ]
            previews = st.session_state["preview_recipes"]
        _render_previews_for_entry(db, schema, previews, _ENTRY_PATH_MANUAL)

    with st.container(border=True):
        st.markdown("**Sync from NYT Cooking**")
        st.caption("Sync a NYT Cooking recipe-box folder.")
        render_nyt_sync_controls()
        _render_previews_for_entry(db, schema, previews, _ENTRY_PATH_NYT)


def _preview_dict(preview: RecipeUrlPreview, *, entry_path: str) -> dict[str, object]:
    data: dict[str, object] = {
        "status": preview.status,
        "url": preview.url,
        "entry_path": entry_path,
    }
    if preview.fields is not None:
        data["fields"] = preview.fields
    if preview.error:
        data["error"] = preview.error
    if preview.duplicate_name:
        data["name"] = preview.duplicate_name
    return data


def _previews_for_ui(db: NotionRecipesDB, urls: list[str]) -> list[dict[str, object]]:
    return [
        _preview_dict(preview, entry_path=_ENTRY_PATH_URL)
        for preview in preview_recipe_urls(db, urls)
    ]


def _recipe_editor_key_prefix(index: int, entry_path: str) -> str:
    if entry_path == _ENTRY_PATH_MANUAL:
        epoch = int(st.session_state.get(_MANUAL_RECIPE_EPOCH_KEY, 0))
        return f"recipe_manual_{epoch}_{index}"
    return f"recipe_{index}"


def _resolve_entry_path(preview: dict[str, object]) -> str:
    path = preview.get("entry_path")
    if isinstance(path, str) and path:
        return path
    if preview.get("status") == "manual":
        return _ENTRY_PATH_MANUAL
    return _ENTRY_PATH_URL


def _render_previews_for_entry(
    db: NotionRecipesDB,
    schema: DatabaseSchema,
    previews: list[dict[str, object]],
    entry_path: str,
) -> None:
    for index, preview in enumerate(previews):
        if _resolve_entry_path(preview) != entry_path:
            continue
        if preview.get("status") == "duplicate":
            st.info(f"Already in Notion: {preview['name']} ({preview['url']})")
            continue
        if preview.get("status") == "saved":
            st.success(f"Saved to Notion: {preview.get('saved_name', 'Recipe')}")
            continue

        _render_recipe_review(db, schema, preview, index)


def _render_recipe_review(
    db: NotionRecipesDB,
    schema: DatabaseSchema,
    preview: dict[str, object],
    index: int,
) -> None:
    status = preview.get("status", "ready")
    fields = preview["fields"]
    recipe_name = fields.get(schema.name_column) or "New recipe"

    if preview.get("error"):
        st.warning(preview["error"])

    title = "Review before saving"
    if status == "manual" and not fields.get(schema.name_column):
        title = "Add recipe details"
    elif status == "ready":
        title = f"Review: {recipe_name}"

    with st.expander(title, expanded=True):
        key_prefix = _recipe_editor_key_prefix(index, _resolve_entry_path(preview))
        edited = _render_recipe_field_editors(schema, fields, key_prefix=key_prefix)

        if st.button("Save to Notion", key=f"save_{index}", type="primary"):
            cleaned = {key: value for key, value in edited.items() if value not in (None, "", [])}
            name = cleaned.get(schema.name_column, "").strip()
            if not name:
                st.warning("Add a recipe name before saving.")
                return
            cleaned[schema.name_column] = name
            if schema.ingredients_column and not cleaned.get(schema.ingredients_column, "").strip():
                st.warning("Add ingredients before saving (one per line).")
                return

            if schema.ingredients_column:
                source_url = cleaned.get(schema.link_column) or preview.get("url")
                cleaned[schema.ingredients_column] = prepare_ingredients_for_notion(
                    cleaned[schema.ingredients_column],
                    source_url=source_url,
                )
                if not cleaned[schema.ingredients_column].strip():
                    st.warning("Add ingredients before saving (one per line).")
                    return

            recipe = db.create_recipe(cleaned)
            invalidate_notion_cache()
            preview["status"] = "saved"
            preview["saved_name"] = recipe.name
            st.rerun()


def _render_recipe_field_editors(
    schema: DatabaseSchema,
    fields: NotionFieldValues,
    *,
    key_prefix: str,
) -> NotionFieldValues:
    edited: NotionFieldValues = {}
    for field_name in ordered_recipe_field_names(schema):
        if field_name not in fields and field_name not in schema.all_columns:
            continue
        value = fields.get(field_name)
        column = schema.all_columns.get(field_name)
        widget_key = f"{key_prefix}_{field_name}"

        if column and column.type in ("select", "status"):
            options = ["", *column.options]
            current = value if value in column.options else ""
            edited[field_name] = st.selectbox(
                field_name,
                options,
                index=options.index(current) if current else 0,
                key=widget_key,
            )
        elif column and column.type == "multi_select":
            edited[field_name] = st.multiselect(
                field_name,
                column.options,
                default=value if isinstance(value, list) else [],
                key=widget_key,
            )
        elif column and column.type == "checkbox":
            edited[field_name] = st.checkbox(
                field_name,
                value=bool(value),
                key=widget_key,
            )
        elif field_name == schema.ingredients_column:
            edited[field_name] = st.text_area(
                field_name,
                value=value or "",
                height=180,
                placeholder="One ingredient per line\neggs\n2 cups flour\n1 lb chicken",
                help="Paste or edit ingredients here. One line per ingredient.",
                key=widget_key,
            )
        elif field_name == schema.instructions_column:
            edited[field_name] = st.text_area(
                field_name,
                value=value or "",
                height=180,
                placeholder="One step per line\nPreheat oven to 350°F\nMix and bake 25 minutes",
                help="Paste or type cooking steps. One line per step.",
                key=widget_key,
            )
        elif field_name == schema.name_column:
            edited[field_name] = st.text_input(
                field_name,
                value=str(value or ""),
                placeholder="Recipe name",
                key=widget_key,
            )
        elif field_name == schema.link_column:
            edited[field_name] = st.text_input(
                field_name,
                value=str(value or ""),
                placeholder="https://... (optional for manual recipes)",
                key=widget_key,
            )
        else:
            edited[field_name] = st.text_input(
                field_name,
                value=str(value or ""),
                key=widget_key,
            )
    return edited
