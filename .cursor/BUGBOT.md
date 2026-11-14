# Bugbot rules (grocery-wizard)

Use these with team rules in Cursor Automations. Standards: **`CONTRIBUTING.md`**. Agent ship/UAT: **`AGENTS.md`**.

## Scope

- **Streamlit UI:** `src/grocery_wizard/ui/` — follow **`docs/ui/ui-map.md`** vocabulary (page / block / control, dot IDs). UI tests import paths from `tests/src/grocery_wizard/ui/ui_source.py` only.
- **Shopping / grocery list:** `src/grocery_wizard/shopping/` — prefer golden-week behavior in **`docs/quality/grocery-quality.md`**.
- **Ingredients / parser:** `src/grocery_wizard/ingredients/` — avoid regressions in normalization patterns.
- **Notion:** read-only CI paths must stay mockable without secrets in tests.

## Blockers (call out clearly)

- Missing or broken tests when behavior changes in covered areas.
- `just check` would fail (ruff, format, pytest).
- Accidental writes to prod Notion in tests or smoke without cleanup docs.
- New path literals in UI tests instead of `ui_source` helpers.
- PRs that omit **`Closes #N`** when the change is meant to finish a backlog issue (GitHub only closes from the PR **description**, not comments).

## Non-blockers (suggest, do not nitpick)

- Structure-only tidy without behavior change (note if a separate commit would help).
- Docs-only gaps when the code change is already clear.

## Verify hint

Recommend **`just check`**; UI changes should mention **`just smoke-ui`** per **`AGENTS.md`**.