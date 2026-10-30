# Notion CI test databases (#426)

GitHub Actions can run **live read-only** pytest against a **CI copy** of your four Grocery Wizard Notion databases. Golden weeks and `just smoke-ui` still run on every PR without secrets; this setup is optional and catches Notion schema / API drift.

Workflow: [`.github/workflows/notion-nightly-readonly.yml`](../.github/workflows/notion-nightly-readonly.yml) (job name *Notion read-only integration*).

## What you need

| Piece | Notes |
| --- | --- |
| **Four CI databases** | Titles should include **`CI`** so they are not confused with `[GW]` production. |
| **`NOTION_API_KEY`** | Same secret name as prod — your Grocery Wizard Notion integration token. |
| **Four `NOTION_CI_*_DATABASE_ID` secrets** | Paste **database** IDs (not data-source / collection IDs). |
| **Integration access** | The integration behind `NOTION_API_KEY` must be **connected** to each CI database (Notion → database → **⋯** → **Connections**). |

Optional: **`NOTION_DATA_SOURCE_ID`** — only if prod uses it (Recipes DB with multiple sources). CI Recipes has a single source; you usually omit this for CI.

**Do not** commit API keys or database IDs into the repo. Set secrets only in GitHub → **Settings** → **Secrets and variables** → **Actions**.

## Recommended database titles and schema

Match production **property names** (see [`src/grocery_wizard/config/README.md`](../src/grocery_wizard/config/README.md)):

| Database | Required properties |
| --- | --- |
| **`[GW CI] Recipes`** | **Name** (title), **Link** (url), **Ingredients** (text). Other recipe columns are optional but help UI smoke tests. |
| **`[GW CI] Pantry Staples`** | **Name**, **Store Aisle** (select — labels from `store_aisles.txt`; run `just sync-pantry-aisles` after copying prod or creating a sparse CI pantry). |
| **`[GW CI] Recurring Weekly Items`** | **Name** only. |
| **`[GW CI] Weekly Meal Plans`** | **Name**, **Week start** (date), **Recipes** (relation → **`[GW CI] Recipes`**). Plan **Name** format: `YYYY-MM-DD_plan` (e.g. `2026-09-13_plan`). |

### Minimal seed data (for live “continue saved plan” smoke)

- **2–3 recipes** with multi-line **Ingredients**.
- **A few pantry rows** with **Store Aisle** set.
- **1 recurring** item (any title).
- **1 saved plan** with **Week start** and **Recipes** linked to at least two CI recipes.

## Copy a database ID from Notion

1. Open the **full-page** database in the browser (not only an inline view).
2. Copy the URL. Example: `https://www.notion.so/a061062d64d64f42a3b48bbb9cdc64ea?v=…`
3. The **32-character hex block** before `?` or `v=` is the database ID. You may paste it **with or without** dashes (`a061062d-64d6-4f42-a3b48bbb9cdc64ea`).

Use the **database** URL from the database’s own page, not a `collection://…` data-source id from API tools.

## GitHub Actions secrets checklist

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
| --- | --- |
| `NOTION_API_KEY` | Integration secret (same token as local prod **if** it has access to CI databases). |
| `NOTION_CI_RECIPE_DATABASE_ID` | `[GW CI] Recipes` database ID |
| `NOTION_CI_PANTRY_DATABASE_ID` | `[GW CI] Pantry Staples` database ID |
| `NOTION_CI_RECURRING_WEEKLY_DATABASE_ID` | `[GW CI] Recurring Weekly Items` database ID |
| `NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID` | `[GW CI] Weekly Meal Plans` database ID |

The workflow maps `NOTION_CI_*` → `NOTION_*_DATABASE_ID` inside the job so pytest calls `load_config()` with CI IDs only. Production IDs in your local `.env` are unchanged.

**Same API key as prod:** fine when the integration is invited to **both** prod and CI databases. If you use a dedicated test workspace, create a separate integration there and paste **that** token as `NOTION_API_KEY` for CI only (prod Streamlit still uses your local `.env`).

## Verify locally (optional)

With `NOTION_API_KEY` in repo-root `.env`:

```bash
export NOTION_CI_RECIPE_DATABASE_ID='…'
export NOTION_CI_PANTRY_DATABASE_ID='…'
export NOTION_CI_RECURRING_WEEKLY_DATABASE_ID='…'
export NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID='…'
export GROCERY_WIZARD_NOTION_CI_LIVE=1
PYTHONPATH=src uv run pytest -k "live and read_only" -q
```

See [`tests/notion_test_env.py`](../tests/notion_test_env.py).

## Example CI workspace (created for this repo)

These databases were created in Notion with the **`[GW CI]`** prefix and minimal seed rows. **Reconnect your Grocery Wizard integration** to each database before CI can read them.

| Database | Notion link | Database ID (for GitHub secret) |
| --- | --- | --- |
| `[GW CI] Recipes` | [Open](https://app.notion.com/p/a061062d64d64f42a3b48bbb9cdc64ea) | `a061062d-64d6-4f42-a3b48bbb9cdc64ea` |
| `[GW CI] Pantry Staples` | [Open](https://app.notion.com/p/f93d5a9ccb254ce58c4f5e4e14bfcef0) | `f93d5a9c-cb25-4ce5-8c4f-5e4e14bfcef0` |
| `[GW CI] Recurring Weekly Items` | [Open](https://app.notion.com/p/b698fd364a6749909c7d005f81d5be9e) | `b698fd36-4a67-4990-9c7d-005f81d5be9e` |
| `[GW CI] Weekly Meal Plans` | [Open](https://app.notion.com/p/7cba2e3a13d14e91b145aff044f9ca56) | `7cba2e3a-13d1-4e91-b145-aff044f9ca56` |

Seed highlights: recipes **CI Lentil Soup**, **CI Tofu Stir Fry**, **CI Simple Salad**; saved plan **`2026-09-13_plan`** (two dinner recipes); pantry **CI olive oil**, **CI garlic**, **CI eggs**; recurring **CI paper towels**.

To duplicate manually instead: in Notion, **Duplicate** each `[GW]` database, rename with **`[GW CI]`**, trim rows, and fix the **Recipes** relation on Weekly Meal Plans to point at **`[GW CI] Recipes`** only.

## Related docs

- [`docs/grocery-quality.md`](grocery-quality.md) — golden weeks + live CI behavior
- GitHub issue [#426](https://github.com/rachelgramlich/grocery-wizard/issues/426)
