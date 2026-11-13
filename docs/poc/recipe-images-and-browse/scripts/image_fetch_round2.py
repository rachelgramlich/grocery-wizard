#!/usr/bin/env python3
"""Round 2: alternate fetch methods for failed POC hosts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import DATA_DIR, OUT_DIR

OUT = OUT_DIR / "round2"
OUT.mkdir(parents=True, exist_ok=True)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

results: list[dict] = []


def record(**kwargs: object) -> None:
    results.append(kwargs)


def download(url: str, dest: Path) -> tuple[bool, int]:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    if not r.ok:
        return False, 0
    dest.write_bytes(r.content)
    return True, len(r.content)


# Instagram oEmbed
ig = "https://www.instagram.com/reel/DZz61Yhx2DC/"
r = requests.get(
    f"https://www.instagram.com/api/v1/oembed/?url={quote(ig, safe='')}",
    headers={"User-Agent": UA},
    timeout=30,
)
if r.ok:
    thumb = r.json().get("thumbnail_url")
    if thumb:
        ok, nbytes = download(thumb, OUT / "instagram_oembed.jpg")
        record(method="instagram_oembed", ok=ok, bytes=nbytes, source_url=ig)
    else:
        record(method="instagram_oembed", ok=False, error="no thumbnail_url")
else:
    record(method="instagram_oembed", ok=False, status=r.status_code)

# TikTok oEmbed
tt_url = "https://www.tiktok.com/t/ZThyD2XYv/"
r = requests.get(
    f"https://www.tiktok.com/oembed?url={quote(tt_url, safe='')}",
    headers={"User-Agent": UA},
    timeout=30,
)
if r.ok:
    data = r.json()
    thumb = data.get("thumbnail_url")
    record(method="tiktok_oembed", ok=bool(thumb), thumbnail=thumb, title=data.get("title"))
    if thumb:
        ok, nbytes = download(thumb, OUT / "tiktok_oembed.jpg")
        record(method="tiktok_oembed_download", ok=ok, bytes=nbytes)
else:
    record(method="tiktok_oembed", ok=False, status=r.status_code, body=r.text[:120])

# Serious Eats with browser UA
se = "https://www.seriouseats.com/the-best-slow-cooked-italian-american-tomato-sauce-red-sauce-recipe"
r = requests.get(se, headers={"User-Agent": UA, "Accept-Language": "en-US"}, timeout=30)
og = None
if r.ok:
    m = re.search(r'property="og:image"\s+content="([^"]+)"', r.text) or re.search(
        r'content="([^"]+)"\s+property="og:image"', r.text
    )
    og = m.group(1) if m else None
    if og:
        ok, nbytes = download(og, OUT / "seriouseats.jpg")
        record(method="seriouseats_og", ok=ok, bytes=nbytes, status=r.status_code)
    else:
        record(method="seriouseats_og", ok=False, status=r.status_code, error="no og:image")
else:
    record(method="seriouseats_og", ok=False, status=r.status_code)

# Allrecipes: timed headless Chrome
ar = "https://www.allrecipes.com/recipe/23600/worlds-best-lasagna/"
html_path = OUT / "allrecipes_headless.html"
try:
    proc = subprocess.run(
        [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--timeout=20000",
            "--dump-dom",
            ar,
        ],
        capture_output=True,
        timeout=25,
        text=True,
    )
    html = proc.stdout
    html_path.write_text(html[:500000], encoding="utf-8")
    m = re.search(r'property="og:image"\s+content="([^"]+)"', html) or re.search(
        r'content="([^"]+)"\s+property="og:image"', html
    )
    og = m.group(1) if m else None
    record(
        method="allrecipes_headless_chrome",
        ok=bool(og),
        og_image=og,
        html_len=len(html),
        exit_code=proc.returncode,
    )
    if og:
        ok, nbytes = download(og, OUT / "allrecipes_headless.jpg")
        record(method="allrecipes_headless_download", ok=ok, bytes=nbytes)
except subprocess.TimeoutExpired:
    record(method="allrecipes_headless_chrome", ok=False, error="chrome timeout 25s")
except Exception as exc:
    record(method="allrecipes_headless_chrome", ok=False, error=str(exc))

(DATA_DIR / "poc-round2-probes.json").write_text(json.dumps(results, indent=2))
(OUT / "round2.json").write_text(json.dumps(results, indent=2))
for row in results:
    print(row)
