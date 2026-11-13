# Recipe image backfill (enhancement draft)

> **Filed:** https://github.com/rachelgramlich/grocery-wizard/issues/490 — use `/work-on-issue 490`.
> **Labels:** `grocery-wizard`, `gw-area-recipes` (UI trigger on Recipe maintenance optional)
> **Enables:** `browse-recipes.md` (Browse grid reads Notion Files column)

## Description

Backfill a Notion **Files** property on the recipe database with a cover/thumbnail image for existing rows that have a **Link** URL but no file in the image column.

**Goals:**

- One-time and repeatable job (like ingredients/metadata backfill on Recipe maintenance).
- **Download once, store in Notion** — upload to the Files column; Browse UI and future features must not depend on hotlinking external CDNs.
- **Graceful failures** — skip or record failure; leave column empty so Browse shows placeholder (do not block batch).
- **Rate limits** — polite delays, concurrency cap, retries with backoff; configurable limits for TikTok/Instagram/NYT/generic hosts.

**Scope of URL handlers (attempt in sensible order per host):**

| Source | Approach |
|--------|----------|
| **NYT Cooking** | Prefer existing NYT client/patterns where applicable; otherwise page fetch |
| **TikTok** | Reuse or extend `scraper.py` TikTok fetch patterns (may be caption-only today — document limits for image extraction) |
| **Instagram** | **`/api/v1/oembed/?url=`** → `thumbnail_url` (prod 2/2); HTML og:image unreliable |
| **General web** | HTML fetch + `og:image` / `twitter:image` (and JSON-LD image if present), following redirects |

Reuse `USER_AGENT` / timeout conventions from `src/grocery_wizard/recipes/scraper.py` where possible; extract shared **image URL resolution** logic so Add Recipe and backfill do not duplicate host-specific code.

**Notion:**

- Configurable Files column name (env or config; default documented e.g. `Photo` or `Image`).
- Notion file upload API for attaching downloaded bytes (respect max file size / type).
- Skip rows that already have ≥1 file in the column.
- Skip rows with empty Link.
- **Dry run** mode: log what would be fetched/uploaded without writes (mirror NYT sync / maintenance backfill UX).

**Surfacing:**

- Minimum: callable from **Recipe maintenance** (`maintenance.backfill_auto` pattern) with progress + summary (`BackfillSummary`-style counts: scanned, updated, skipped, failed).
- Optional CLI entry point for local batch runs.

**Add Recipe (same epic as backfill — required):**

| Flow | When |
|------|------|
| `add.url` | On Save to Notion after validation |
| `add.manual` | On save if Link is non-empty |
| `add.nyt` | On each new row created by NYT sync |

- Use same resolver + Notion Files upload as backfill.
- **Never fail** the save if image fails; tell the user: *Saved; no cover image was found for this link.*
- Optional success message when image attaches; no image preview required in v1.

**Testing:**

- Unit tests with mocked HTTP responses for og:image, NYT, and failure paths.
- No live TikTok/Instagram in CI.

## Expected behavior & manual test hints

**Surface:** Recipe maintenance → automatic backfill section (or new block), with dry run.

**Steps:**

1. In Notion, pick a recipe with Link, empty Files column → run **dry run** → see planned fetch host + image URL.
2. Run backfill for one recipe → Files column has an image; Browse page (once shipped) shows it.
3. Recipe with broken Link → failure counted in summary; column stays empty.
4. Recipe that already has image → skipped.
5. Batch of 50+ → completes without rate-limit ban (throttling observable in logs/progress).
6. `just check` passes.

## Area

recipes

## Acceptance criteria

- [ ] Identifies recipes: non-empty **Link**, empty configurable **Files** image column.
- [ ] Resolvers for NYT, TikTok, Instagram, and generic **og:image** (documented fallbacks).
- [ ] Downloads image bytes and **uploads to Notion Files** (no hotlink-only storage).
- [ ] Dry run + live run with progress and summary (updated / skipped / failed).
- [ ] Rate limiting and retries; failures do not abort entire batch.
- [ ] Recipes without successful fetch remain without Files (Browse placeholder).
- [ ] Config for column name; schema query includes Files column for recipe list.
- [ ] Tests with mocked HTTP; no secrets required in CI.
- [ ] Document column setup in repo docs (Notion household + CI).
- [ ] Add Recipe URL, manual (with Link), and NYT sync create paths attach image best-effort with user messaging.

## Non-goals

- OCR or video-frame extraction for TikTok/Instagram when HTML has no image.
- Copyright review of fetched images (household use; user owns recipe links).

## Prod estimate (Nov 2025)

280 with Link / 307 total; ~**98%** fetch success projected (~274 rows). See #490 Chat sync comment.

## Related

- #491 Browse, #492 tap V2
