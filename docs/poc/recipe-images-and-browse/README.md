# Recipe images + Browse recipes — POC & design pack

Engineering reference for GitHub issues **[#490](https://github.com/rachelgramlich/grocery-wizard/issues/490)** (backfill + Add Recipe images), **[#491](https://github.com/rachelgramlich/grocery-wizard/issues/491)** (Browse grid), **[#492](https://github.com/rachelgramlich/grocery-wizard/issues/492)** (card tap V2).

This folder is **not** production code. Scripts are smoke tests and resolvers to lift into `src/` when implementing.

## Layout

| Path | Purpose |
|------|---------|
| [`design/image-resolvers.md`](design/image-resolvers.md) | URL → bytes resolver chain, Add Recipe behavior |
| [`design/browse-ui.md`](design/browse-ui.md) | Streamlit Browse page layout (not the red/green POC report) |
| [`data/prod-image-fetch-projection.json`](data/prod-image-fetch-projection.json) | Prod Notion sample (Nov 2025): ~98% success among 280 rows with Link |
| [`data/poc-round1-results.json`](data/poc-round1-results.json) | Fixed-URL round 1 fetch results |
| [`data/poc-round2-probes.json`](data/poc-round2-probes.json) | Alternate methods (Instagram oEmbed, etc.) |
| [`mock/browse-recipes-ui-mock.html`](mock/browse-recipes-ui-mock.html) | Static UI reference (open in browser) |
| [`scripts/`](scripts/) | Runnable POC scripts (write under `out/`; gitignored) |

Issue drafts: [`docs/issues/`](../issues/README.md) (GitHub issues are canonical).

## Run POC scripts (from repo root)

```bash
# Round 1: fixed URLs → download images + report.html under out/
PYTHONPATH=src uv run python docs/poc/recipe-images-and-browse/scripts/image_fetch_poc.py

# Round 2: alternate fetch probes (Instagram oEmbed, headless Allrecipes timeout, …)
PYTHONPATH=src uv run python docs/poc/recipe-images-and-browse/scripts/image_fetch_round2.py

# Prod: read recipe DB (needs NOTION_* in .env or env) + sample 121 URLs — read-only HTTP
PYTHONPATH=src uv run python docs/poc/recipe-images-and-browse/scripts/prod_image_fetch_sample.py
```

Outputs:

- `docs/poc/recipe-images-and-browse/out/` — downloads, `report.html`, latest sample JSON (gitignored)
- `data/*.json` — refreshed when you re-run scripts (commit updates if you want to snapshot new numbers)

## Implementation map

| Product area | Issue | Start here |
|--------------|-------|------------|
| Notion Files backfill + Add Recipe attach | #490 | `design/image-resolvers.md`, lift logic from `scripts/image_fetch_poc.py` |
| Browse page | #491 | `design/browse-ui.md`, `mock/browse-recipes-ui-mock.html` |
| Card → weekly plan | #492 | `design/browse-ui.md` (V2 section) |

**POC HTML report** (red/green cards) is for resolver debugging only — **not** the Browse UI (#491).
