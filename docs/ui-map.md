# Grocery Wizard UI map

Vocabulary for issues, feedback, tests, and agents.

**Weekly tab behavior** (rail, collapse, happy path): see [`weekly-flow-ui.md`](weekly-flow-ui.md).

## Terms

| Term | Meaning |
|------|---------|
| **Page** | Top segmented nav item, or pseudo-page `global` for app-wide controls |
| **Block** | Named UI region; use `{page}.{block}` IDs (nested blocks add segments) |
| **Control** | One widget; use `{page}.{block}.{control}` when precision matters |

**Store layout:** say **store aisle**, not “section” (legacy code may still use `section` in identifiers).

## Pages

| Slug | Segmented control label |
|------|-------------------------|
| `global` | *(not in picker)* |
| `weekly` | Create weekly plan |
| `add` | Add Recipe |
| `pantry` | Pantry & recurring |
| `maintenance` | Recipe maintenance |

Constants: `src/grocery_wizard/ui/ids.py`, labels: `src/grocery_wizard/ui/pages/__init__.py`.

## Global controls

| ID | UI |
|----|-----|
| `global.global.page_picker` | Page segmented control |
| `global.global.refresh` | Refresh from Notion |
| `global.global.feedback` | Send feedback |
| `global.global.loading` | Global loading banner |

## Blocks by page

### `weekly` (order matters)

Rail steps (user-facing, not numbered): **Get started** → **Plan meals** → **Grocery list** (includes review + copy). Details: [`weekly-flow-ui.md`](weekly-flow-ui.md).

| Block ID | UI (internal / legacy labels) |
|----------|-------------------------------|
| `weekly.plan_start` | How do you want to start? |
| `weekly.meals` | Plan meals — meal count |
| `weekly.meals.build` | Plan meals — build / pin / **Build my plan** |
| `weekly.meals.list` | Plan meals — your meals (swap) |
| `weekly.meals.save` | Plan meals — save to Notion |
| `weekly.grocery_pre_build` | Grocery list — pre-build options |
| `weekly.grocery_recipe_review` | Grocery list — review ingredients (main path) |
| `weekly.grocery_result` | Grocery list — built list |
| `weekly.grocery_result.summary` | Grocery list — summary (build result) |
| `weekly.grocery_result.customize` | Grocery list — customize / copy |

### `add`

| Block ID | UI |
|----------|-----|
| `add.url` | Recipe URL |
| `add.manual` | Type it in myself |
| `add.nyt` | Sync from NYT Cooking |

### `pantry`

| Block ID | UI |
|----------|-----|
| `pantry.recurring` | Recurring weekly items |
| `pantry.staples` | Pantry |

### `maintenance`

| Block ID | UI |
|----------|-----|
| `maintenance.meal_plan_status` | Meal plan status |
| `maintenance.backfill_auto` | Automatic backfill |
| `maintenance.backfill_manual` | Manual backfill in Notion |

## Code layout

| Area | Python |
|------|--------|
| App entry, page routing | `ui/app.py` |
| IDs | `ui/ids.py` |
| Page labels / slugs | `ui/pages/__init__.py` |
| Page bodies | `ui/pages/*.py`, `ui/pages/weekly_plan/` |
| Weekly grocery build logic | `ui/grocery_flow.py`, `ui/grocery_helpers.py` |
| Shared widgets | `ui/loading.py`, `ui/feedback.py`, `ui/notion_cache.py`, … |

Feedback backlog **Surface** should use a **page slug** (`weekly`, `add`, …) unless a block ID is more helpful.
