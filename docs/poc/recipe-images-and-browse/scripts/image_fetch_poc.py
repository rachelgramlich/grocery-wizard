#!/usr/bin/env python3
"""POC: resolve and download recipe hero images from several URL types."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import sys
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import DATA_DIR, OUT_DIR

OUT = OUT_DIR
OUT.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
TIMEOUT = 30
DELAY_S = 1.0

CASES: list[tuple[str, str, str]] = [
    (
        "nyt_dead",
        "NYT (404 recipe)",
        "https://cooking.nytimes.com/recipes/1019049-simple-pasta",
    ),
    (
        "nyt_ok",
        "NYT Cooking",
        "https://cooking.nytimes.com/recipes/1026918-crispy-potato-quesadillas",
    ),
    (
        "nyt_ok2",
        "NYT Cooking",
        "https://cooking.nytimes.com/recipes/1022255-sesame-salmon-bowls",
    ),
    (
        "general_bbc",
        "General (BBC Good Food)",
        "https://www.bbcgoodfood.com/recipes/easy-pancakes",
    ),
    (
        "general_allrecipes",
        "General (Allrecipes, bot block)",
        "https://www.allrecipes.com/recipe/23600/worlds-best-lasagna/",
    ),
    (
        "tiktok",
        "TikTok",
        "https://www.tiktok.com/t/ZThyD2XYv/",
    ),
    (
        "instagram",
        "Instagram reel",
        "https://www.instagram.com/reel/DZz61Yhx2DC/",
    ),
]


@dataclass
class FetchResult:
    case_id: str
    source_type: str
    page_url: str
    ok: bool
    stage: str
    image_url: str | None
    local_path: str | None
    bytes_size: int | None
    content_type: str | None
    http_status: int | None
    error: str | None


def _is_tiktok(url: str) -> bool:
    return "tiktok.com" in urlparse(url).netloc.lower()


def _is_instagram(url: str) -> bool:
    return "instagram.com" in urlparse(url).netloc.lower()


def _json_ld_images(soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                img = node.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    urls.append(img)
                elif isinstance(img, list):
                    for item in img:
                        if isinstance(item, str) and item.startswith("http"):
                            urls.append(item)
                        elif isinstance(item, dict) and item.get("url"):
                            urls.append(str(item["url"]))
                elif isinstance(img, dict) and img.get("url"):
                    urls.append(str(img["url"]))
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return urls


def _meta_images(soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    for prop in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            urls.append(str(tag["content"]).strip())
    return urls


def _regex_og_image(html: str) -> list[str]:
    patterns = [
        r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'"og:image"\s*:\s*"([^"]+)"',
    ]
    found: list[str] = []
    for pat in patterns:
        found.extend(re.findall(pat, html, flags=re.IGNORECASE))
    return found


def _tiktok_cover_from_rehydration(html: str) -> str | None:
    match = re.search(
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    blob = json.dumps(data)
    # Prefer photomode stills over avatar thumbs.
    candidates = re.findall(
        r"https://[^\"\\]+tiktokcdn[^\"\\]+(?:photomode|image)[^\"\\]*",
        blob,
    )
    if not candidates:
        candidates = re.findall(r"https://[^\"\\]+\.(?:jpeg|jpg|webp)(?:\?[^\"\\]*)?", blob)
    return candidates[0] if candidates else None


def resolve_image_url(page_url: str, html: bytes) -> tuple[str | None, str]:
    text = html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    for extractor_name, candidates in (
        ("og/meta", _meta_images(soup)),
        ("json-ld", _json_ld_images(soup)),
        ("regex", _regex_og_image(text)),
    ):
        for raw in candidates:
            if not raw:
                continue
            img = urljoin(page_url, raw.strip())
            if img.startswith("http"):
                return img, extractor_name
    return None, "none"


def fetch_page(url: str) -> tuple[bytes | None, int | None, str | None]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        return resp.content, resp.status_code, None if resp.ok else f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return None, None, str(exc)


def download_image(image_url: str, dest: Path) -> tuple[bool, int | None, str | None, str | None]:
    try:
        resp = requests.get(
            image_url,
            headers={"User-Agent": USER_AGENT, "Referer": image_url},
            timeout=TIMEOUT,
            stream=True,
        )
        if not resp.ok:
            return False, None, resp.headers.get("Content-Type"), f"image HTTP {resp.status_code}"
        data = resp.content
        if len(data) < 200:
            return False, None, resp.headers.get("Content-Type"), "image too small"
        ct = (resp.headers.get("Content-Type") or "").lower()
        ext = ".jpg"
        if "png" in ct:
            ext = ".png"
        elif "webp" in ct:
            ext = ".webp"
        elif "gif" in ct:
            ext = ".gif"
        path = dest.with_suffix(ext)
        path.write_bytes(data)
        return True, len(data), ct, None
    except requests.RequestException as exc:
        return False, None, None, str(exc)


def run_case(case_id: str, source_type: str, page_url: str) -> FetchResult:
    time.sleep(DELAY_S)
    html, status, page_err = fetch_page(page_url)
    if html is None:
        return FetchResult(
            case_id,
            source_type,
            page_url,
            False,
            "fetch_page",
            None,
            None,
            None,
            None,
            status,
            page_err,
        )

    page_text = html.decode("utf-8", errors="replace")
    img_url, resolver = resolve_image_url(page_url, html)
    if not img_url and _is_tiktok(page_url):
        tik = _tiktok_cover_from_rehydration(page_text)
        if tik:
            img_url = tik
            resolver = "tiktok:rehydration"

    if not img_url:
        # TikTok/Instagram often omit og:image without login — note in error
        hint = ""
        if _is_tiktok(page_url) or _is_instagram(page_url):
            hint = " (no og:image; TikTok may need rehydration JSON)"
        return FetchResult(
            case_id,
            source_type,
            page_url,
            False,
            f"resolve_image:{resolver}",
            None,
            None,
            None,
            None,
            status,
            f"No image URL in HTML{hint}",
        )

    dest = OUT / case_id
    ok, nbytes, ct, dl_err = download_image(img_url, dest)
    local_path = None
    if ok and dest.with_suffix(".jpg").exists():
        local_path = str(dest.with_suffix(".jpg"))
    else:
        for ext in (".png", ".webp", ".gif", ".jpg"):
            p = dest.with_suffix(ext)
            if p.exists():
                local_path = str(p)
                break

    return FetchResult(
        case_id,
        source_type,
        page_url,
        bool(ok and local_path),
        f"download via {resolver}" if ok else f"download after {resolver}",
        img_url,
        local_path,
        nbytes,
        ct,
        status,
        dl_err,
    )


def write_html(results: list[FetchResult]) -> Path:
    cards = []
    for r in results:
        status = "SUCCESS" if r.ok else "FAILED"
        color = "#1a7f37" if r.ok else "#cf222e"
        img_html = ""
        if r.local_path and Path(r.local_path).is_file():
            rel = Path(r.local_path).name
            img_html = f'<img src="{escape(rel)}" alt="downloaded" style="max-width:100%;max-height:220px;border-radius:8px;"/>'
        else:
            img_html = '<div style="height:120px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#666;">No image saved</div>'
        cards.append(
            f"""
            <section style="border:2px solid {color};border-radius:12px;padding:16px;background:#fff;">
              <h3 style="margin:0 0 8px;">{escape(r.source_type)} <span style="color:{color};font-size:14px;">{status}</span></h3>
              <p style="font-size:12px;word-break:break-all;margin:0 0 8px;"><a href="{escape(r.page_url)}">{escape(r.page_url)}</a></p>
              {img_html}
              <dl style="font-size:12px;margin:12px 0 0;">
                <dt>Stage</dt><dd>{escape(r.stage)}</dd>
                <dt>Image URL</dt><dd style="word-break:break-all;">{escape(r.image_url or "—")}</dd>
                <dt>Bytes</dt><dd>{r.bytes_size or "—"}</dd>
                <dt>Error</dt><dd>{escape(r.error or "—")}</dd>
              </dl>
            </section>
            """
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Image fetch POC</title>
<style>body{{font-family:system-ui,sans-serif;background:#fafafa;margin:24px;}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;max-width:1200px;}}
h1{{margin-bottom:8px;}}</style></head>
<body>
<h1>Recipe image fetch POC</h1>
<p>Downloaded once to disk (not hotlinked). Delay {DELAY_S}s between page fetches.</p>
<div class="grid">{"".join(cards)}</div>
</body></html>"""
    report = OUT / "report.html"
    report.write_text(html, encoding="utf-8")
    return report


def main() -> None:
    results = [run_case(cid, stype, url) for cid, stype, url in CASES]
    payload = json.dumps([asdict(r) for r in results], indent=2)
    (OUT / "results.json").write_text(payload)
    (DATA_DIR / "poc-round1-results.json").write_text(payload)
    write_html(results)
    for r in results:
        icon = "OK" if r.ok else "FAIL"
        print(f"{icon}\t{r.source_type}\t{r.stage}\t{r.error or r.bytes_size}")


if __name__ == "__main__":
    main()
