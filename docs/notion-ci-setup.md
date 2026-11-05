# Notion CI test databases (#426)

GitHub Actions can run **live read-only** pytest against a **CI copy** of your four Grocery Wizard Notion databases. Golden weeks and `just smoke-ui` still run on every PR without secrets; this setup is optional and catches Notion schema / API drift.

Household production is **one** Streamlit Community Cloud app ([`docs/household-deploy.md`](household-deploy.md)); experiment on **`[GW CI]`** via local Streamlit (`NOTION_CI_*` / `GROCERY_WIZARD_NOTION_CI_LIVE`) or GitHub/Cursor CI secrets—not a second Cloud deploy ([#356](https://github.com/rachelgramlich/grocery-wizard/issues/356)).

Workflow: [`.github/workflows/notion-nightly-readonly.yml`](../.github/workflows/notion-nightly-readonly.yml) (display name *Notion read-only integration*). Runs on **`pull_request`** to **`main`** (same repo, when secrets are set) and **`workflow_dispatch`** — no scheduled cron.

## What you need

| Piece | Notes |
| --- | --- |
| **Four CI databases** | Titles should include **`CI`** so they are not confused with `[GW]` production. |
| **`NOTION_CI_API_KEY`** | GitHub Actions secret — integration token with access to CI databases (may be the same token as local prod). |
| **Four `NOTION_CI_*_DATABASE_ID` secrets** | Paste **database** IDs (not data-source / collection IDs). |
| **Integration access** | The integration behind `NOTION_CI_API_KEY` must be **connected** to each CI database (Notion → database → **⋯** → **Connections**). |

Optional: **`NOTION_DATA_SOURCE_ID`** — only if prod uses it (Recipes DB with multiple sources). CI Recipes has a single source; you usually omit this for CI.

**Do not** commit API keys or database IDs into the repo. Set secrets in GitHub → **Settings** → **Secrets and variables** → **Actions**, and (for Cloud Agents) the same names in **Cursor → Cloud Agents → environment secrets** for this repo.

### Cursor Cloud Agents

Use the **same five secret names** as the GitHub checklist below. Agents map them to `NOTION_*` at runtime via `tests/notion_test_env.py` (see **`AGENTS.md`** — preflight one-liner). Target **`[GW CI]`** databases only; prefer read-only smoke and revert any test writes.

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
3. The **32-character hex block** before `?` or `v=` is the database ID. Paste **with or without** dashes; the app normalizes to standard UUID form (example: `a061062d-64d6-4f42-a3b4-8bbb9cdc64ea` — note **12** hex chars in the last segment, not 16).

Use the **database** URL from the database’s own page, not a `collection://…` data-source id from API tools.

## GitHub Actions secrets checklist

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
| --- | --- |
| `NOTION_CI_API_KEY` | Integration secret (same token as local prod **if** it has access to CI databases). |
| `NOTION_CI_RECIPE_DATABASE_ID` | `[GW CI] Recipes` database ID |
| `NOTION_CI_PANTRY_DATABASE_ID` | `[GW CI] Pantry Staples` database ID |
| `NOTION_CI_RECURRING_WEEKLY_DATABASE_ID` | `[GW CI] Recurring Weekly Items` database ID |
| `NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID` | `[GW CI] Weekly Meal Plans` database ID |
| `NOTION_CI_DEBUG_LOGS_DATABASE_ID` *(optional)* | `[GW CI] List Debug Logs` — if unset, CI uses the weekly plans ID so `load_config()` passes (read-only smoke does not write logs). |

The workflow maps `NOTION_CI_API_KEY` → `NOTION_API_KEY` and each `NOTION_CI_*_DATABASE_ID` → `NOTION_*_DATABASE_ID` inside the job so pytest calls `load_config()` with CI credentials only. Production IDs in your local `.env` are unchanged.

**Same API key as prod:** fine when the integration is invited to **both** prod and CI databases. If you use a dedicated test workspace, create a separate integration there and paste **that** token as `NOTION_CI_API_KEY` for CI only (prod Streamlit still uses `NOTION_API_KEY` in your local `.env`).

## Verify locally (optional)

With `NOTION_API_KEY` in repo-root `.env`:

```bash
export NOTION_CI_RECIPE_DATABASE_ID='…'
export NOTION_CI_PANTRY_DATABASE_ID='…'
export NOTION_CI_RECURRING_WEEKLY_DATABASE_ID='…'
export NOTION_CI_WEEKLY_MEAL_PLANS_DATABASE_ID='…'
export GROCERY_WIZARD_NOTION_CI_LIVE=1
PYTHONPATH=src uv run python -m grocery_wizard.integrations.notion_ci_schema
PYTHONPATH=src uv run pytest -k "live and read_only" -q
```

`notion_ci_schema` checks that each CI database is reachable, required columns exist (with clear errors on rename), and `query_recipes` returns parseable rows when pages exist (empty DB is a skip note, not a failure).

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
