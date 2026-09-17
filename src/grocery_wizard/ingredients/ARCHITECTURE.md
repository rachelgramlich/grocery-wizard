# Ingredients module architecture

Grocery Wizard treats recipe ingredients in two separate pipelines. They share helpers under `_cleaning.py` and `_patterns.py`, but **call different entry points** depending on whether you are writing to Notion or building a shopping list.

## Storage pipeline (Notion `Ingredients` column)

**Goal:** Persist one line per grocery item in a stable `{quantity} {name}` (or lightly cleaned raw) form when adding or syncing recipes.

| Stage | Module | Typical functions |
| --- | --- | --- |
| Scrape / read URL | `recipes/scraper.py` | raw HTML → line list |
| Drop junk & split merges | `ingredients/normalize.py` | `drop_junk_ingredient_lines`, `expand_ingredient_line`, `is_instruction_line`, … |
| Format for Notion | `ingredients/parsed.py` | `format_ingredient_for_storage`, `minimal_clean_for_storage` (NYT) |
| Orchestration | `ingredients/sync.py` | `prepare_ingredients_for_notion`, `merge_ingredients`, dev backfill/reconcile |

**Name for dedup / merge:** `parsed.name_from_stored_line` — parses the qty/name embedded in a storage line. Do **not** use this for grocery-list display keys.

Flow:

```text
recipe URL or paste
  → normalize (line filters only)
  → parsed.format_ingredient_for_storage
  → Notion rich_text Ingredients
```

## Grocery-list pipeline (read Notion → shop)

**Goal:** Canonical lowercase item names, combined amounts, pantry exclusion, aisle sort — at list generation time only (see package README).

| Stage | Module | Typical functions |
| --- | --- | --- |
| Read plan + Notion | `shopping/grocery_list.py` | recipe ingredients text |
| Parse directives | `ingredients/sync.py` | `parse_ingredients_text` |
| Normalize & amounts | `ingredients/normalize.py` | `normalize_ingredient`, `parse_amount`, `aggregate_amounts` |
| Display & aisles | `shopping/grocery_list.py`, `shopping/store_aisles.py` | formatted lines, aisle keywords |

**Canonical grocery name:** `normalize.normalize_ingredient` — handles checklist prefixes, `<br/>` splits, prep stripping, and stored-line fallbacks.

Flow:

```text
Notion Ingredients (+ week plan)
  → parse_ingredients_text (removals, directives)
  → normalize_ingredient / parse_amount
  → aggregate_amounts + format_grocery_item
  → shopping list output
```

## Naming: avoid `ingredient_name` confusion

Three different “ingredient name” helpers existed historically:

| Symbol | Where | Use when |
| --- | --- | --- |
| `normalize_ingredient` | `normalize.py` | Grocery keys, meal-plan ingredient filter, validation |
| `name_from_stored_line` | `parsed.py` | Merge/dedup of Notion storage lines in `sync.py` |
| `ingredient_name` | `parsed.py` | Deprecated alias → `name_from_stored_line` |
| `ingredient_name` | `shopping/store_aisles.py` | Strip qty prefix from **formatted list lines** for aisle keywords |

Import from **`ingredients/parsed.py`**, **`ingredients/normalize.py`**, or **`ingredients/sync.py`** depending on pipeline (see table below).

## Module map

| File | Role |
| --- | --- |
| `_patterns.py` | Shared regexes and unit/noun lists |
| `_cleaning.py` | Shared line prep, compound splits |
| `parsed.py` | Library-backed parse → storage string; parse stored lines |
| `normalize.py` | Grocery normalization, amounts, aggregation |
| `sync.py` | Notion sync, merge, refresh, review formatting |

## Tests

- Unit cases: `tests/src/grocery_wizard/ingredients/test_normalize.py`, `test_sync.py`
- End-to-end storage → grocery: `tests/src/grocery_wizard/ingredients/test_pipeline.py` (via `pipeline_helpers.py`)
- Full app path: `dev validate-pipeline` (Notion → plan → list)
