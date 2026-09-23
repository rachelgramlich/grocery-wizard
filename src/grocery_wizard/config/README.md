# Grocery Wizard config files

Paths and env loading live in `__init__.py`. This folder holds **shared product config** only; personal household data lives in Notion.

## What stays in the repo

| File | Role |
|------|------|
| **`store_aisles.txt`** | Source of truth for store walk order, aisle labels, and ingredient keywords. Edit here and commit — section headers like `# --- Produce ---`. |
| **`__init__.py`** | Notion credentials and database IDs. |

`store_aisles.txt` should **not** move to Notion; it is shared app configuration, not personal household data. Rationale and boundaries (repo rules vs Notion pantry rows): [decision #268](https://github.com/rachelgramlich/grocery-wizard/issues/268).

## Personal data (Notion only)

Pantry staples, recurring weekly items, and saved weekly meal plans live in **Notion databases** (same integration as Recipes). They are **not** committed in this repo.

| Data | Notion database | Properties |
|------|-----------------|------------|
| Pantry staples | Pantry | **Name** (title), **Store Aisle** or **Aisle** (select — labels from `store_aisles.txt`) |
| Recurring weekly items | Recurring | **Name** (title) only |
| Saved weekly meal plans | Weekly plans | **Name**, **Week start**, **Version**, **Recipes** (relation → Recipes) |

Plan **Name** is the sole identifier (e.g. `2026-09-13_plan_v1`); no slug column.

Current-week session state may still use `.local/grocery_wizard/week_plan.json` (gitignored) until fully Notion-backed for “this session” if needed.

### Recurring items: template vs one run

1. **Template** — default list every grocery run (Notion recurring DB).
2. **This run only** — additions/removals for a single session; must not update the template unless the user explicitly edits defaults.

Pantry edits from the UI similarly distinguish one-off vs changing the saved staple list in Notion.

## Notion env

Required for Grocery Wizard:

- `NOTION_API_KEY`
- `NOTION_RECIPE_DATABASE_ID` (legacy alias `NOTION_DATABASE_ID`)
- `NOTION_PANTRY_DATABASE_ID`
- `NOTION_RECURRING_WEEKLY_DATABASE_ID`
- `NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID`

Cloud agents use the same names as Secrets.

Optional: `NOTION_DATA_SOURCE_ID` — force a specific data source when a Notion database exposes multiple sources (see `integrations/notion_data_source.py`). Recipes DB resolution prefers the source whose schema includes **Link** when unset.

### Pantry `Aisle` select options

When you create the pantry database, add an **Aisle** column (legacy **Section** still works). Option labels should match the display labels in `store_aisles.txt`. Reclassify rows by editing keywords in `store_aisles.txt` and updating aisle values in Notion (or via the Streamlit pantry UI).
