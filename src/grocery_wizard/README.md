# Grocery Wizard

Notion-driven recipe tool: add recipes, plan meals, generate grocery lists.

## What do I run?

All commands run from the repo root:

```shell
uv run python -m src.grocery_wizard.cli <command>
```

### I found a new recipe online

```shell
uv run python -m src.grocery_wizard.cli add-recipe https://example.com/my-recipe
```

Saves the recipe to Notion and scrapes ingredients from the page.

### I need to plan dinners or build a grocery list

Use the **Streamlit app** (primary workflow):

```shell
just grocery-ui
```

Plan meals, adjust pantry exclusions, add recurring items, and export your list from the browser. The app persists plans in Notion and keeps a local `.local/grocery_wizard/week_plan.json` cache for diversity hints.

### My pantry staples changed

```shell
uv run python -m src.grocery_wizard.cli edit-pantry
```

`edit-pantry` updates your **Notion pantry** database — items there won't show up on your shopping list.

### I want to sync my NYT Cooking recipe box to Notion

NYT credentials come from environment variables only (no `nyt auth` command).

#### Get credentials from your browser

1. Log into [NYT Cooking](https://cooking.nytimes.com).
2. Open DevTools → **Application** (Chrome) or **Storage** (Firefox) → **Cookies** → `cooking.nytimes.com`.
3. Copy the **NYT-S** cookie value → set as `NYT_S_COOKIE`.
4. Copy **regi_id** from the **regi_cookie** value (or paste the full cookie; the numeric id is extracted automatically) → set as `NYT_REGI_ID`.

#### Set environment variables

**Local** — add to `.env` in the repo root (see `.env.example`):

```shell
NYT_S_COOKIE=your-nyt-s-cookie-value
NYT_REGI_ID=12345678
```

`NYT_USER_ID` is accepted as an alias for `NYT_REGI_ID`.

**Cloud Agent / dashboard** — add the same names as Secrets (`NYT_S_COOKIE`, `NYT_REGI_ID` or `NYT_USER_ID`).

#### Sync in the Streamlit app

1. Run `just grocery-ui` (or `uv run streamlit run src/grocery_wizard/ui/app.py`).
2. Under the title, expand **Sync from NYT Cooking**.
3. Pick a recipe-box folder (or **All saved recipes**), optionally enable **Dry run**, then click **Sync to Notion** or **Preview sync**.

NYT sync adds **name, link, classified metadata, and the "Synced from NYT recipe box" checkbox** — not ingredients. Add a **checkbox** column with that exact name in Notion (or set `GROCERY_WIZARD_NYT_SYNCED_COLUMN` if you name it differently). Fill ingredients later with `dev backfill-ingredients` or when ingredient parsing (#21) lands.

After sync, the app shows a **Metadata review** expander. The last sync report is also available from **Last sync metadata review**. Ask your agent to fix flagged recipes if needed.

**Weeknight friendly** is set automatically when you add any recipe (`add-recipe`, NYT sync, or the Streamlit UI). For **Dinner** recipes it is checked when total cook time is under 60 minutes (from the scraper's JSON-LD data or NYT API) or the title suggests a quick/easy dish (weeknight, one-pot, sheet pan, stir fry, etc.). You do not need to set the checkbox manually during review.

## Command cheat sheet

| Command | What it does |
|---------|--------------|
| `add-recipe` | Save a new recipe from a URL into Notion |
| `edit-pantry` | Edit what's always in your kitchen (won't appear on shopping list) |
| Streamlit → **Sync from NYT Cooking** | Import saved NYT recipes into Notion (folder picker, dry run; skips duplicates) |

### Dev / maintenance commands

Use when you edit Notion directly, need to refresh ingredient data, or debug schema issues.

| Command | What it does |
|---------|--------------|
| `dev backfill-ingredients` | Fill in missing ingredient lists from recipe links |
| `dev reconcile-ingredients` | Update ingredients where you already have some (keeps your edits) |
| `dev refresh-all-ingredients` | Re-download ingredients for every recipe |
| `dev audit-recipes` | Show which recipes need attention |
| `dev show-schema` | Show how Notion columns are detected |

```shell
# Recipes added in Notion with a link but no ingredients
uv run python -m src.grocery_wizard.cli dev backfill-ingredients

# Preview without writing
uv run python -m src.grocery_wizard.cli dev backfill-ingredients --dry-run

# Reconcile recipes you already edited in Notion
uv run python -m src.grocery_wizard.cli dev reconcile-ingredients

# Nuclear option: re-scrape everything
uv run python -m src.grocery_wizard.cli dev refresh-all-ingredients

# Health check
uv run python -m src.grocery_wizard.cli dev audit-recipes
uv run python -m src.grocery_wizard.cli dev show-schema
```

## Project layout

Grocery Wizard is a package under `src/grocery_wizard/`. Folders group code by **what it does**; tests mirror the same folders under `tests/src/grocery_wizard/`.

### Source (`src/grocery_wizard/`)

| Folder | Key files | Responsibility |
|--------|-----------|----------------|
| `cli/` | `main.py` | Command-line entry (`add-recipe`, `edit-pantry`, `dev …`; Streamlit for planning) |
| `ui/` | `app.py`, `sections/`, `notion_cache.py` | Streamlit app: segmented sections (weekly plan, add recipe, pantry & recurring) |
| `config/` | `__init__.py`, `store_aisles.txt` | Env settings and committed store walk order |
| `integrations/` | `notion.py`, `notion_household.py`, `nyt_cooking.py` | Notion API; pantry/recurring/plans DBs; NYT sync |
| `recipes/` | `scraper.py`, `classify.py`, `add_recipe.py` | Scrape URLs, classify metadata, save new recipes |
| `ingredients/` | `parsed.py`, `sync.py`, `ARCHITECTURE.md` | Two pipelines: storage vs grocery list (`normalize`); see doc |
| `planning/` | `meal_planner.py` | Meal suggestion and filter logic (Streamlit + dev validation) |
| `shopping/` | `grocery_list.py`, `pantry.py` | Build shopping list; pantry load/match/edit |
| `dev/` | `audit.py` | Recipe health checks |
| `lib/` | `prompts.py` | Shared interactive prompts |

### Tests (`tests/src/grocery_wizard/`)

Same subfolders as source — e.g. `recipes/test_scraper.py` tests `recipes/scraper.py`.

### Local runtime data (gitignored)

| Path | Purpose |
|------|---------|
| `.local/grocery_wizard/week_plan.json` | This week's planned recipe names |
| `.env` | Notion API key and database IDs, NYT credentials (see `.env.example`) |

### Entry points

```shell
# CLI (primary)
uv run python -m src.grocery_wizard.cli <command>

# Streamlit (secondary) — run from repository root so .streamlit/config.toml loads
just grocery-ui
# or: uv run streamlit run src/grocery_wizard/ui/app.py
```

```
grocery-wizard/
├── src/grocery_wizard/          # package (table above)
├── tests/src/grocery_wizard/    # tests (mirrors package folders)
└── .local/grocery_wizard/       # your week plan (not committed)
```

## Architecture notes

Ingredient **storage** (Notion write) and **grocery-list** (read/normalize) pipelines are documented in [`ingredients/ARCHITECTURE.md`](ingredients/ARCHITECTURE.md).

## How ingredients are stored

Ingredients are scraped **once** and stored in Notion's `Ingredients` column — the full scraped list, including pantry staples:

1. **Add recipe** — scrapes the URL and saves all raw ingredient lines to `Ingredients`
2. **Grocery list** — reads `Ingredients` from Notion; normalizes and excludes pantry staples by default

Normalization and pantry exclusion happen at grocery-list time only — not when adding or syncing to Notion.

## One-time setup

1. Create a [Notion integration](https://www.notion.so/my-integrations) and copy the API key.
2. Share your **Recipes** database with the integration (⋯ → Connections).
3. Create Notion databases for pantry staples, recurring weekly items, and saved weekly meal plans (see `config/README.md`). Connect the same integration to each.
4. Copy `.env.example` to `.env` and fill in:
   - `NOTION_API_KEY` — integration secret
   - `NOTION_RECIPE_DATABASE_ID` — Recipes database ID
   - `NOTION_PANTRY_DATABASE_ID`, `NOTION_RECURRING_WEEKLY_DATABASE_ID`, `NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID`
5. From repo root: `just setup`
6. Verify: `uv run python -m src.grocery_wizard.cli dev show-schema`
7. Sync pantry aisle select options: `uv run python -m src.grocery_wizard dev sync-notion-pantry-sections`

## Meal planning

Use **`just grocery-ui`** for weekly planning. Default filters in the UI match the former CLI defaults:

| Filter | Default |
|--------|---------|
| Meal | Dinner |
| Dinner: Weeknight Friendly | yes |

Suggestions maximize variety across **Protein**, **Dinner Category**, and **Cuisine**. Plans are stored in Notion; the app also writes `{"recipes": ["Name1", ...]}` to `.local/grocery_wizard/week_plan.json` for session hints and `dev validate-pipeline`.

## Configuration vs local data

Committed config lives in the package; per-week data stays local:

| Path | Committed? | Purpose |
|------|------------|---------|
| `src/grocery_wizard/config/store_aisles.txt` | yes | Store walk order, aisle labels, and ingredient keywords |
| `src/grocery_wizard/config/__init__.py` | yes | Env vars and Notion database IDs |
| Notion pantry / recurring / weekly-plans DBs | — | Pantry staples, recurring items, saved meal plans |
| `.local/grocery_wizard/week_plan.json` | no | This week's planned recipes (session cache) |

## Pantry staples

`edit-pantry` edits your Notion pantry database, grouped by section headers. Interactive options:

- **a** — add an item (pick a section or create one)
- **r** — remove by number or name
- **e** — open a temp file in `$EDITOR`, then sync back to Notion on quit
- **q** — save and quit

Matching uses phrase boundaries: `kosher salt` matches pantry item `salt`, but `beef` does not match `beef stock`.

## Recurring weekly items

The **Notion recurring weekly items** database lists defaults added every week (berries, milk, etc.). In the Streamlit grocery flow you can accept, edit, or skip them for the current week — and optionally save edits back to Notion for future weeks.

## Grocery list aisle order

The app sorts items by store walk order using aisle section headers. Edit `src/grocery_wizard/config/store_aisles.txt` to change walk order, labels, or keywords:

```text
# --- fruit: Fruit ---
banana
berries

# --- vegetables: Vegetables ---
onion
garlic
...
```

Unmatched items land in **Other** (always last). Longer keyword phrases win over shorter ones (`potato chips` → snacks, not produce).

## Streamlit UI

```shell
just grocery-ui
# or: uv run streamlit run src/grocery_wizard/ui/app.py
```

Sections (segmented control): **Create weekly plan** (meal planning, ingredient review, grocery list), **Add recipe**, **Pantry & recurring**.

**Phone / remote access:** see [docs/remote-access.md](docs/remote-access.md) (local Wi‑Fi + CLI by default; always-on host only if we implement #138).

UI performance research (Streamlit rerun model, Notion caching, phased roadmap): [`docs/ui-performance-research.md`](../../docs/ui-performance-research.md).

## Supported recipe sources

Most recipe blogs with structured HTML or JSON-LD work well. When available, **total cook time** is read from JSON-LD (`totalTime`, or `prepTime` + `cookTime`) for weeknight-friendly classification. TikTok and Instagram are **partially supported** — ingredients must appear in the caption text. When scraping fails, paste ingredients manually into Notion or use a blog link.

## Notion database schema (auto-detected)

Key columns:

| Column | Type | Used for |
|--------|------|----------|
| Name | title | Recipe name |
| Link | url | Source URL |
| Ingredients | rich_text | Full raw ingredient lines |
| Meal | select | Breakfast, Lunch, Dinner, … |
| Protein | multi_select | Chicken, Fish, Beans, … |
| Cuisine | multi_select | Italian, Asian, Mexican, … |
| Dinner Category | multi_select | Curry, Pasta, Bowl, … |
| Dinner: Weeknight Friendly | checkbox | Meal-planning filter |
| Synced from NYT recipe box | checkbox | Set automatically by NYT recipe-box sync in the Streamlit app |

Optional env overrides: `GROCERY_WIZARD_NAME_COLUMN`, `GROCERY_WIZARD_LINK_COLUMN`, `GROCERY_WIZARD_INGREDIENTS_COLUMN`.
