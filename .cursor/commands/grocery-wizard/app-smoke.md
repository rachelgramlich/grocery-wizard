---
name: app-smoke
description: Holistic headless + browser smoke before UI work is "done"
---

# App smoke (holistic sign-off)

**Purpose:** Catch production-only UI crashes (e.g. saved-plan load `TypeError`) before merge. Run this **before** claiming a UI PR is ready.

## Required: headless holistic smoke (CI-safe)

```bash
just smoke-ui
```

Same tests also run under **`just check`** / **`just ci`** (marker `holistic_ui_smoke`).

**Covers (mocked Notion):**

- Import/load `src/grocery_wizard/ui/app.py` (no module-level `ImportError`)
- AppTest first run (global refresh, feedback, weekly plan entry)
- Weekly plan entry → **`cached_saved_plans`** / saved plan list (#417 path)
- Continue saved plan → meals step (session only, no Notion writes)
- **Dev mode → Dev: Final list** on the golden weekly fixture (real build/merge/sort; see `docs/grocery-quality.md`)
- **Pantry & recurring**, **Add Recipe**, **Recipe maintenance** pages open

Implementation: `tests/src/grocery_wizard/ui/test_holistic_ui_smoke_apptest.py`, helpers in `tests/src/grocery_wizard/ui/ui_source.py`.

### Optional: live Notion (same file, skipped without secrets)

When `NOTION_API_KEY` is real (not the pytest placeholder):

```bash
just smoke-ui   # includes optional live cases when env is configured
```

Read-only: real saved-plan list and optional continue → meal-count gate. **Do not** save plans or write pantry during smoke.

## Required for UI PRs: browser smoke (when Notion preflight succeeds)

**Preflight (local prod `NOTION_API_KEY` in env or `.env`):**

```bash
test -n "${NOTION_API_KEY:-}" && PYTHONPATH=src uv run python -c "from grocery_wizard.config import load_config; load_config(); print('notion ok')"
```

**Preflight (Cursor Cloud Agents with `NOTION_CI_*` secrets — `[GW CI]` databases only):**

```bash
PYTHONPATH=src uv run python -c "from tests.notion_test_env import apply_notion_ci_env_for_live_tests; apply_notion_ci_env_for_live_tests(); from grocery_wizard.config import load_config; load_config(); print('notion ok')"
```

Optional: `export GROCERY_WIZARD_NOTION_CI_LIVE=1` when a prod key exists in `.env` but smoke should hit CI data. See **`docs/notion-ci-setup.md`** and **`AGENTS.md`**.

When preflight prints `notion ok`:

1. `just grocery-ui` (or confirm port **8501**)
2. Walk **every primary page** via the page picker
3. On **Create weekly plan**: confirm mode picker loads; open **Continue a saved weekly plan** and confirm the saved-plan list renders (no error banner / traceback)
4. Prefer read-only paths; undo any accidental Notion writes before sign-off

Use browser automation (Cloud agents: computerUse). Record a short walkthrough when the mandate asks for artifacts.

## PR / chat sign-off lines

State **both**:

- **`Holistic smoke: ran`** (`just smoke-ui`) or **`Holistic smoke: skipped — <reason>`**
- **`Browser smoke: ran`**, **`Browser smoke: skipped — <reason>`**, or **`Browser smoke: N/A (non-UI)`**

See **`AGENTS.md`** → Manual verification.
