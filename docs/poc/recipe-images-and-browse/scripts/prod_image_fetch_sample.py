#!/usr/bin/env python3
"""Read-only: sample prod recipe links and test image resolution."""

from __future__ import annotations

import json
import os
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlparse

import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import DATA_DIR, OUT_DIR, REPO_ROOT

load_dotenv(REPO_ROOT / ".env", override=False)
if not os.environ.get("NOTION_DEBUG_LOGS_DATABASE_ID"):
    w = os.environ.get("NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID")
    if w:
        os.environ["NOTION_DEBUG_LOGS_DATABASE_ID"] = w

from grocery_wizard.config import load_config
from grocery_wizard.integrations.notion import NotionRecipesDB

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 25
DELAY = 0.35


def bucket(link: str) -> str:
    h = urlparse(link.strip()).netloc.lower().replace("www.", "")
    if "cooking.nytimes.com" in h or h.endswith("nytimes.com"):
        return "nyt"
    if "tiktok.com" in h:
        return "tiktok"
    if "instagram.com" in h:
        return "instagram"
    if "allrecipes.com" in h:
        return "allrecipes"
    if "seriouseats.com" in h:
        return "seriouseats"
    if "foodnetwork.com" in h:
        return "foodnetwork"
    return "other_web"


def tiktok_cover(html: str) -> str | None:
    match = re.search(
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        blob = json.dumps(json.loads(match.group(1)))
    except json.JSONDecodeError:
        return None
    urls = re.findall(
        r"https://[^\"\\]+tiktokcdn[^\"\\]+(?:photomode|origin\.image)[^\"\\]*",
        blob,
    )
    return urls[0] if urls else None


def resolve(link: str) -> tuple[bool, str]:
    host_bucket = bucket(link)
    time.sleep(DELAY)
    if host_bucket == "instagram":
        r = requests.get(
            f"https://www.instagram.com/api/v1/oembed/?url={quote(link, safe='')}",
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        if r.ok and r.json().get("thumbnail_url"):
            return True, "instagram_oembed"
        return False, "instagram_oembed_fail"
    try:
        r = requests.get(
            link,
            headers={"User-Agent": UA, "Accept-Language": "en-US"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return False, f"fetch_error:{exc.__class__.__name__}"
    if not r.ok:
        return False, f"http_{r.status_code}"
    html = r.text
    for pat in (
        r'property="og:image"\s+content="([^"]+)"',
        r'content="([^"]+)"\s+property="og:image"',
    ):
        m = re.search(pat, html)
        if m:
            return True, "og_image"
    if host_bucket == "tiktok" and tiktok_cover(html):
        return True, "tiktok_rehydration"
    return False, "no_image_url"


def main() -> None:
    db = NotionRecipesDB(load_config())
    recipes = db.query_recipes()
    with_link = [(r.name, r.link.strip()) for r in recipes if (r.link or "").strip()]

    by_bucket: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for name, link in with_link:
        by_bucket[bucket(link)].append((name, link))

    population = Counter(bucket(link) for _, link in with_link)
    sampled: list[tuple[str, str, str]] = []
    rng = random.Random(42)
    for b, rows in by_bucket.items():
        if b == "nyt":
            pick = rows if len(rows) <= 80 else rng.sample(rows, 80)
        else:
            pick = rows
        for name, link in pick:
            sampled.append((b, name, link))

    results: list[dict] = []
    for b, name, link in sampled:
        ok, how = resolve(link)
        results.append({"bucket": b, "name": name, "link": link, "ok": ok, "how": how})

    sample_rates: dict[str, tuple[int, int]] = {}
    for b in population:
        sub = [x for x in results if x["bucket"] == b]
        if sub:
            wins = sum(1 for x in sub if x["ok"])
            sample_rates[b] = (wins, len(sub))

    projected_wins = 0.0
    for b, count in population.items():
        if b in sample_rates:
            w, n = sample_rates[b]
            rate = w / n
        else:
            rate = 0.0
        projected_wins += count * rate

    other_hosts = Counter(
        urlparse(link).netloc.lower().replace("www.", "")
        for b, _, link in sampled
        if b == "other_web"
    )

    out = {
        "prod_total_recipes": len(recipes),
        "with_link": len(with_link),
        "no_link": len(recipes) - len(with_link),
        "population_by_bucket": dict(population),
        "sample_tested": len(sampled),
        "sample_success_rate_by_bucket": {b: round(w / n, 3) for b, (w, n) in sample_rates.items()},
        "projected_success_among_with_link_pct": round(100 * projected_wins / len(with_link), 1),
        "projected_fail_among_with_link_pct": round(100 * (1 - projected_wins / len(with_link)), 1),
        "projected_success_count_rounded": round(projected_wins),
        "other_web_hosts_in_sample": dict(other_hosts),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "prod-image-fetch-projection.json").write_text(json.dumps(out, indent=2))
    (OUT_DIR / "prod-image-fetch-sample.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
