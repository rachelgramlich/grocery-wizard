---
name: grocery-quality-review
description: Sign-off on weekly grocery list correctness (golden weeks + smoke + optional browser)
---

# Grocery quality review

Use this instead of **`/architecture-review`** when the question is **“is the exported grocery list correct?”** Architecture review checks repo standards; this checks **output**.

## Required (automated)

```bash
just golden-grocery
just smoke-ui
```

See **`docs/grocery-quality.md`**.

## Optional (when Notion preflight succeeds)

1. `just grocery-ui` with **`GROCERY_WIZARD_DEV_UI=1`**
2. Dev jump or manual path through **Create grocery list** using your golden meal set
3. Compare copy text to the fixture (or run `just export-golden-week … --dry-run` after a plan change)

## When filing bugs

Every user-visible list defect should add or extend a file under `tests/fixtures/golden_grocery_weeks/`, not only a single-line normalize test.

## PR sign-off lines

- **`Golden grocery: ran`** (`just golden-grocery`) or **`Golden grocery: skipped — <reason>`**
- **`Holistic smoke: ran`** / skipped (same as **`/app-smoke`**)
