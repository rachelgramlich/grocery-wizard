# Image resolvers (for #490)

## Prod expectations (household DB, Nov 2025)

See [`data/prod-image-fetch-projection.json`](../data/prod-image-fetch-projection.json): 307 recipes, 280 with Link, projected **~98%** image URL resolution with the resolver chain below.

## Resolver order

1. Fetch page (or host-specific API).
2. `og:image` / Twitter / JSON-LD `image`.
3. **Instagram:** `GET https://www.instagram.com/api/v1/oembed/?url=` → `thumbnail_url`.
4. **TikTok:** parse `__UNIVERSAL_DATA_FOR_REHYDRATION__` for `tiktokcdn` still URL when `og:image` missing.
5. Download bytes → **Notion Files upload** (never store hotlinked TikTok/IG CDN URLs long-term).

## Known failures (prod sample)

- YouTube `watch` URLs (no still in v1).
- Some food blogs without og still.
- Food Network (1 row in sample) — may need follow-up.
- Bot-blocked sites (Allrecipes class) — rare in prod; mark failed.

## Add Recipe flows (required with #490)

On **Save to Notion** / NYT sync create:

- Run same resolver; **never fail** save if image fails.
- User message: *“Saved to Notion. No cover image was found for this link.”*
- Surfaces: `add.url`, `add.manual` (when Link set), `add.nyt`.

## POC scripts

- [`scripts/image_fetch_poc.py`](../scripts/image_fetch_poc.py) — round 1 matrix.
- [`scripts/image_fetch_round2.py`](../scripts/image_fetch_round2.py) — oEmbed / headless probes.
- [`scripts/prod_image_fetch_sample.py`](../scripts/prod_image_fetch_sample.py) — stratified prod URLs.
