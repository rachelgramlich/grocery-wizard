# Grocery list quality (golden weeks + invariants)

Unit tests on one ingredient line miss bugs that only show up on a **whole weekly list** (duplicates, aisle order, review round-trip, extras/recurring merge).

## Golden weekly plans

Fixtures live in `tests/fixtures/golden_grocery_weeks/*.json`. Each file includes:

- Planned recipes and Notion ingredient text
- Pantry / recurring / extra-items inputs
- `expect_grocery_lines`: ordered export lines (same as copy button)

**Run:**

```bash
just golden-grocery
```

These tests run the **full export pipeline** in `src/grocery_wizard/shopping/weekly_grocery_export.py` (review formatting → `build_grocery_result_payload` → `compute_grocery_drafts` → copy text).

**Add your real saved week** (requires Notion credentials):

```bash
# From a Notion saved plan (easiest):
just export-golden-week notion_2026_11_01_plan --from-saved-plan 2026-11-01_plan

# Or name recipes by hand:
just export-golden-week my_real_week "Recipe A" "Recipe B" "Recipe C"

# Preview JSON only:
just export-golden-week my_real_week "Recipe A" --dry-run
```

Commit the new JSON. CI will fail if the list changes until you update `expect_grocery_lines` on purpose.

## List invariants (every golden week)

`src/grocery_wizard/shopping/grocery_invariants.py` checks:

- No duplicate normalized item keys
- Every line is idempotent under `normalize_grocery_list_item`
- Lines are in store-aisle order
- No checklist markup (`[ ]`) in export lines

## Holistic UI smoke

`just smoke-ui` includes a **CI-safe** AppTest: Dev mode → pick golden recipes → **Dev: Final list** → assert the same export lines and invariants. That uses the real UI session path, not a mocked `build_grocery_list`.

**Extras text area:** Dev jump goes straight to the final list and skips the **Create grocery list** pre-build step (where you type extras). The holistic test sets session state for extras when the fixture has them, but it does not click through pre-build. For weeks with non-empty `extra_items`, trust **`just golden-grocery`** for full coverage. A second smoke that walks pre-build is optional later.

## When a user reports a bad line

1. Fix the parser/shopping bug.
2. Add a **golden week** (or extend an existing one), not only a single-line normalize test.
3. Optional: keep a minimal line case if it documents a tricky edge.

## Architecture review vs grocery quality

`/architecture-review` checks repo standards and boundaries. It does **not** assert grocery output.

For release-style sign-off on list correctness, use:

- `just golden-grocery`
- `just smoke-ui`
- `/app-review` with the golden week meal set (browser)
- `/triage-feedback-inbox` → every list bug promotes a golden fixture task

## Live Notion (#426)

CI still uses a fake Notion DB. Nightly read-only tests against a **test workspace** catch schema drift; golden weeks catch **list logic** regressions without secrets.
