"""Download recipe cover images and upload them to a Notion Files column."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.grocery_wizard.integrations.notion import NotionRecipesDB
from src.grocery_wizard.recipes.recipe_image_resolver import (
    ImageResolveError,
    ResolvedRecipeImage,
    download_recipe_image_bytes,
    resolve_recipe_image_url,
)

logger = logging.getLogger(__name__)

NO_COVER_IMAGE_USER_MESSAGE = "Saved to Notion. No cover image was found for this link."
COVER_IMAGE_FAILED_USER_MESSAGE = "Saved to Notion. Could not upload a cover image for this link."


@dataclass(frozen=True, slots=True)
class RecipeImageAttachResult:
    ok: bool
    resolved: ResolvedRecipeImage | None = None
    error: str | None = None
    user_message: str | None = None


def attach_recipe_cover_image(
    db: NotionRecipesDB,
    page_id: str,
    link_url: str,
    *,
    dry_run: bool = False,
) -> RecipeImageAttachResult:
    """Best-effort cover upload; never raises (call after recipe create succeeds)."""
    column = db.schema.image_column
    if not column:
        return RecipeImageAttachResult(ok=True, user_message=None)

    url = (link_url or "").strip()
    if not url:
        return RecipeImageAttachResult(
            ok=False,
            error="no_link",
            user_message=NO_COVER_IMAGE_USER_MESSAGE,
        )

    try:
        resolved = resolve_recipe_image_url(url)
    except ImageResolveError as exc:
        logger.info("Recipe image resolve failed for %s: %s", url, exc)
        return RecipeImageAttachResult(
            ok=False,
            error=str(exc),
            user_message=NO_COVER_IMAGE_USER_MESSAGE,
        )

    if dry_run:
        return RecipeImageAttachResult(ok=True, resolved=resolved)

    try:
        downloaded = download_recipe_image_bytes(resolved.image_url)
        db.upload_recipe_image_file(
            page_id,
            column,
            filename=downloaded.filename,
            data=downloaded.data,
            content_type=downloaded.content_type,
        )
    except (ImageResolveError, ValueError, OSError) as exc:
        logger.warning("Recipe image attach failed for %s: %s", url, exc)
        return RecipeImageAttachResult(
            ok=False,
            resolved=resolved,
            error=str(exc),
            user_message=COVER_IMAGE_FAILED_USER_MESSAGE,
        )

    return RecipeImageAttachResult(ok=True, resolved=resolved)
