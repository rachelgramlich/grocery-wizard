"""Tests for recipe cover image URL resolution."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.grocery_wizard.recipes.recipe_image_resolver import (
    ImageResolveError,
    resolve_recipe_image_url,
)


def test_resolve_generic_og_image() -> None:
    html = """
    <html><head>
      <meta property="og:image" content="https://cdn.example.com/hero.jpg" />
    </head></html>
    """
    response = MagicMock(status_code=200, text=html, content=html.encode())
    with patch(
        "src.grocery_wizard.recipes.recipe_image_resolver._get_with_retries",
        return_value=response,
    ):
        resolved = resolve_recipe_image_url(
            "https://example.com/recipe",
            host_delay_seconds=0,
        )
    assert resolved.image_url == "https://cdn.example.com/hero.jpg"
    assert resolved.method == "html_meta"


def test_resolve_instagram_uses_oembed() -> None:
    oembed = MagicMock(
        status_code=200,
        json=lambda: {"thumbnail_url": "https://cdn.instagram.com/thumb.jpg"},
    )
    with patch(
        "src.grocery_wizard.recipes.recipe_image_resolver._get_with_retries",
        return_value=oembed,
    ):
        resolved = resolve_recipe_image_url(
            "https://www.instagram.com/reel/abc/",
            host_delay_seconds=0,
        )
    assert resolved.host == "instagram"
    assert resolved.method == "instagram_oembed"
    assert resolved.image_url.endswith("thumb.jpg")


def test_resolve_tiktok_rehydration() -> None:
    payload = {
        "__DEFAULT_SCOPE__": {
            "webapp.video-detail": {
                "itemInfo": {
                    "itemStruct": {
                        "video": {"cover": "https://tiktok.cdn/cover.webp"},
                    },
                },
            },
        },
    }
    html = f'<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">{json.dumps(payload)}</script></html>'
    response = MagicMock(status_code=200, text=html, content=html.encode())
    with patch(
        "src.grocery_wizard.recipes.recipe_image_resolver._get_with_retries",
        return_value=response,
    ):
        resolved = resolve_recipe_image_url(
            "https://www.tiktok.com/@u/video/1",
            host_delay_seconds=0,
        )
    assert resolved.method == "tiktok_rehydration"
    assert "tiktok.cdn" in resolved.image_url


def test_resolve_missing_image_raises() -> None:
    html = "<html><head><title>No image</title></head></html>"
    response = MagicMock(status_code=200, text=html, content=html.encode())
    with (
        patch(
            "src.grocery_wizard.recipes.recipe_image_resolver._get_with_retries",
            return_value=response,
        ),
        pytest.raises(ImageResolveError),
    ):
        resolve_recipe_image_url("https://example.com/empty", host_delay_seconds=0)
