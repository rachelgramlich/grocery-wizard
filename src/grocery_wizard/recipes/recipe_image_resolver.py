"""Resolve a recipe cover image URL from a recipe Link (no Notion upload)."""

from __future__ import annotations

import html
import json
import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.grocery_wizard.ingredients.parsed import is_nyt_cooking_url
from src.grocery_wizard.recipes.scraper import REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

INSTAGRAM_OEMBED_URL = "https://www.instagram.com/api/v1/oembed/"
DEFAULT_HTTP_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.5
DEFAULT_HOST_DELAY_SECONDS = 0.35

_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/avif",
        "image/heic",
    }
)
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


class ImageResolveError(Exception):
    """Could not find a cover image URL for this recipe link."""


@dataclass(frozen=True, slots=True)
class ResolvedRecipeImage:
    page_url: str
    image_url: str
    host: str
    method: str


@dataclass(frozen=True, slots=True)
class DownloadedRecipeImage:
    data: bytes
    content_type: str
    filename: str


def recipe_link_host(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    host = host.removeprefix("www.")
    if "tiktok.com" in host:
        return "tiktok"
    if "instagram.com" in host:
        return "instagram"
    if "cooking.nytimes.com" in host or "nytimes.com" in host:
        return "nyt"
    return "other_web"


def _sleep_between_hosts(host: str, *, delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def _get_with_retries(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = REQUEST_TIMEOUT,
    max_retries: int = DEFAULT_HTTP_RETRIES,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
) -> requests.Response:
    last_exc: Exception | None = None
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=hdrs, timeout=timeout, allow_redirects=True)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < max_retries - 1:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(backoff_seconds * (attempt + 1))
        else:
            return response
    if last_exc is not None:
        raise ImageResolveError(f"HTTP error fetching {url}: {last_exc}") from last_exc
    raise ImageResolveError(f"HTTP error fetching {url}")


def _absolute_url(page_url: str, raw: str) -> str:
    raw = html.unescape(raw.strip())
    if raw.startswith("//"):
        return f"https:{raw}"
    if raw.startswith(("http://", "https://")):
        return raw
    if raw.startswith("/"):
        parsed = urlparse(page_url)
        return f"{parsed.scheme}://{parsed.netloc}{raw}"
    return raw


def _meta_image_from_soup(page_url: str, soup: BeautifulSoup) -> str | None:
    for prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if isinstance(tag, Tag) and tag.get("content"):
            candidate = _absolute_url(page_url, str(tag["content"]))
            if candidate.startswith("http"):
                return candidate

    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.IGNORECASE)}):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        url = _json_ld_image_url(data)
        if url:
            return _absolute_url(page_url, url)
    return None


def _json_ld_image_url(data: object) -> str | None:
    if isinstance(data, list):
        for item in data:
            url = _json_ld_image_url(item)
            if url:
                return url
        return None
    if not isinstance(data, dict):
        return None
    if data.get("@type") == "ImageObject" and isinstance(data.get("url"), str):
        return data["url"]
    image = data.get("image")
    if isinstance(image, str) and image.strip():
        return image.strip()
    if isinstance(image, dict) and isinstance(image.get("url"), str):
        return image["url"]
    if isinstance(image, list):
        for item in image:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                return item["url"]
    graph = data.get("@graph")
    if isinstance(graph, list):
        return _json_ld_image_url(graph)
    return None


def _tiktok_cover_from_html(page_url: str, html_text: str) -> str | None:
    soup = BeautifulSoup(html_text, "html.parser")
    script = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
    if not script or not script.string:
        return None
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return None
    item = (
        data.get("__DEFAULT_SCOPE__", {})
        .get("webapp.video-detail", {})
        .get("itemInfo", {})
        .get("itemStruct")
    )
    if not isinstance(item, dict):
        return None
    video = item.get("video") or {}
    if not isinstance(video, dict):
        return None
    for key in ("cover", "dynamicCover", "originCover", "shareCover"):
        raw = video.get(key)
        if isinstance(raw, str) and raw.startswith("http"):
            return raw
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry.startswith("http"):
                    return entry
    return _meta_image_from_soup(page_url, soup)


def _instagram_thumbnail_url(page_url: str) -> str | None:
    oembed = f"{INSTAGRAM_OEMBED_URL}?url={quote(page_url, safe='')}"
    response = _get_with_retries(oembed, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    thumbnail = payload.get("thumbnail_url")
    if isinstance(thumbnail, str) and thumbnail.startswith("http"):
        return thumbnail
    return None


def resolve_recipe_image_url(
    page_url: str,
    *,
    host_delay_seconds: float = DEFAULT_HOST_DELAY_SECONDS,
) -> ResolvedRecipeImage:
    """Return a downloadable image URL for ``page_url`` (recipe Link column)."""
    stripped = page_url.strip()
    if not stripped:
        raise ImageResolveError("Empty recipe link")

    host = recipe_link_host(stripped)
    _sleep_between_hosts(host, delay_seconds=host_delay_seconds)

    if host == "instagram":
        thumb = _instagram_thumbnail_url(stripped)
        if thumb:
            return ResolvedRecipeImage(
                page_url=stripped,
                image_url=thumb,
                host=host,
                method="instagram_oembed",
            )
        raise ImageResolveError("No Instagram thumbnail (oEmbed)")

    response = _get_with_retries(stripped)
    if response.status_code >= 400:
        raise ImageResolveError(f"HTTP {response.status_code} for recipe page")

    html_text = response.text
    soup = BeautifulSoup(response.content, "html.parser")

    if host == "tiktok":
        cover = _tiktok_cover_from_html(stripped, html_text)
        if cover:
            return ResolvedRecipeImage(
                page_url=stripped,
                image_url=cover,
                host=host,
                method="tiktok_rehydration",
            )
        raise ImageResolveError("No TikTok cover in page data")

    meta = _meta_image_from_soup(stripped, soup)
    if meta:
        method = "nyt_og" if is_nyt_cooking_url(stripped) else "html_meta"
        return ResolvedRecipeImage(
            page_url=stripped,
            image_url=meta,
            host=host,
            method=method,
        )
    raise ImageResolveError("No og:image, twitter:image, or JSON-LD image")


def _guess_filename(content_type: str, image_url: str) -> str:
    lowered = (content_type or "").split(";", 1)[0].strip().lower()
    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/avif": ".avif",
        "image/heic": ".heic",
    }.get(lowered, "")
    if not ext:
        path = urlparse(image_url).path.lower()
        for candidate in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if path.endswith(candidate):
                ext = candidate if candidate != ".jpeg" else ".jpg"
                break
    if not ext:
        ext = ".jpg"
    return f"recipe-cover{ext}"


def download_recipe_image_bytes(
    image_url: str,
    *,
    max_bytes: int = _MAX_IMAGE_BYTES,
    host_delay_seconds: float = DEFAULT_HOST_DELAY_SECONDS,
) -> DownloadedRecipeImage:
    """Download image bytes once (for Notion upload, not hotlink storage)."""
    host = recipe_link_host(image_url)
    _sleep_between_hosts(host, delay_seconds=host_delay_seconds)
    response = _get_with_retries(image_url, headers={"Accept": "image/*,*/*"})
    if response.status_code >= 400:
        raise ImageResolveError(f"HTTP {response.status_code} downloading image")

    content_type = (response.headers.get("Content-Type") or "image/jpeg").split(";", 1)[0].strip()
    if (
        content_type
        and content_type not in _IMAGE_CONTENT_TYPES
        and not content_type.startswith("image/")
    ):
        raise ImageResolveError(f"Unexpected content type: {content_type}")

    data = response.content
    if len(data) > max_bytes:
        raise ImageResolveError(f"Image too large ({len(data)} bytes)")
    if not data:
        raise ImageResolveError("Empty image response")

    filename = _guess_filename(content_type, image_url)
    normalized_type = content_type or "image/jpeg"
    return DownloadedRecipeImage(data=data, content_type=normalized_type, filename=filename)
