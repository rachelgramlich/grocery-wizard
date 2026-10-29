# Ingredients module architecture

Grocery Wizard treats recipe ingredients in two separate pipelines. They share helpers under `_cleaning.py` and `_patterns.py`, but **call different entry points** depending on whether you are writing to Notion or building a shopping list.

## Storage pipeline (Notion `Ingredients` column) — **the only full parser**

**Goal:** When a recipe is added or synced, persist one stable line per grocery item: `{quantity} {name}` (prep stripped, package sizes like `(15-ounce)` dropped, dual `cup/240 grams` collapsed at save time).

| Stage | Module | Typical functions |
| --- | --- | --- |
| Scrape / read URL | `recipes/scraper.py` | raw HTML → line list |
| Drop junk & split legacy merges | `ingredients/normalize.py` | `drop_junk_ingredient_lines`, … |
| Format for Notion | `ingredients/parsed.py` | `format_ingredient_for_storage` |
| Orchestration | `ingredients/sync.py` | `prepare_ingredients_for_notion`, `merge_ingredients` |

**All new recipe save paths** call `prepare_ingredients_for_notion`, which always runs `format_ingredient_for_storage`. There is no NYT “minimal clean” branch.

Measurement cleanup (`normalize_measurement_text`: strip trailing `/240 grams`, `packed` before units, `11/2` typos, etc.) runs only inside `_normalize_unicode_for_storage`, used by the storage formatter — **not** on grocery-list read.

Example: `2 (15-ounce) cans beans` → stored in Notion as `2 cans beans`.

Flow:

```text
recipe URL or paste
  → normalize (line filters only)
  → format_ingredient_for_storage  (full parser + measurement cleanup)
  → Notion rich_text Ingredients
```

Existing Notion rows are never bulk-rewritten. Re-save a recipe when you want its lines upgraded.

## Grocery-list pipeline (read Notion → shop)

**Goal:** Read what Notion stores, merge amounts, pantry exclusion, aisle sort — **no second full parse / no `format_ingredient_for_storage`.**

| Stage | Module | Typical functions |
| --- | --- | --- |
| Read plan + Notion | `shopping/grocery_list.py` | recipe ingredients text |
| Parse directives | `ingredients/sync.py` | `parse_ingredients_text` |
| Read stored shape | `ingredients/normalize.py` | `parse_notion_ingredient_for_grocery` → `parse_stored_ingredient` |
| Display & aisles | `shopping/grocery_list.py`, `shopping/store_aisles.py` | `format_grocery_item`, aisle keywords |

`parse_stored_ingredient` uses read-side unicode only. It still understands common stored shapes, including `(15-ounce)` before `can`/`cans`, so a Notion line that was never re-saved can still list correctly without rewriting Notion.

Flow:

```text
Notion Ingredients (+ week plan)
  → parse_ingredients_text (removals, directives)
  → parse_notion_ingredient_for_grocery (read only)
  → aggregate_amounts + format_grocery_item
  → merge/dedupe, pantry skip, aisle sort
```

## Naming: avoid `ingredient_name` confusion

| Symbol | Where | Use when |
| --- | --- | --- |
| `parse_notion_ingredient_for_grocery` | `normalize.py` | **Notion → weekly grocery list** |
| `format_ingredient_for_storage` | `parsed.py` | **Recipe add / sync → Notion** |
| `normalize_ingredient` / `parse_amount` | `normalize.py` | Filters, review UI, legacy callers (may re-format raw text) |
| `name_from_stored_line` | `parsed.py` | Merge/dedup of Notion storage lines in `sync.py` |
| `ingredient_name` | `shopping/store_aisles.py` | Strip qty prefix from **formatted list lines** for aisle keywords |

## Module map

| File | Role |
| --- | --- |
| `_patterns.py` | Shared regexes and unit/noun lists |
| `_cleaning.py` | Shared line prep, compound splits, `normalize_measurement_text` |
| `parsed.py` | Library-backed parse → storage string; parse stored lines |
| `normalize.py` | Grocery read helper, filters, aggregation |
| `sync.py` | Notion sync, merge, refresh, review formatting |

## Tests

- Unit cases: `tests/src/grocery_wizard/ingredients/test_normalize.py`, `test_sync.py`
- End-to-end storage → grocery: `tests/src/grocery_wizard/ingredients/test_pipeline.py` (via `pipeline_helpers.py`)
