## Description

Run this sign-off procedure **once on `main`** after **everything in the merge checklist below** has landed—not after each PR alone.

**Scope today:**

1. **Architecture stack (Tiers B–E):** [#519](https://github.com/rachelgramlich/grocery-wizard/pull/519) → [#520](https://github.com/rachelgramlich/grocery-wizard/pull/520) → [#522](https://github.com/rachelgramlich/grocery-wizard/pull/522) → [#523](https://github.com/rachelgramlich/grocery-wizard/pull/523)
2. **Tidy stack (structure-only, stacked on the architecture tip):** [#525](https://github.com/rachelgramlich/grocery-wizard/pull/525) → [#526](https://github.com/rachelgramlich/grocery-wizard/pull/526) → [#527](https://github.com/rachelgramlich/grocery-wizard/pull/527), plus **any further `chore(tidy):` PRs** stacked above #527 before calling UAT done.

Intended behavior: **no intentional behavior change** (path dedupe, guards, docs, lint rules). **Tier C** (grocery build) and **Tier D** (Notion layout) still warrant extra attention in smoke.

**If anything fails:** do **not** revert the whole stack by default. File a **bug** (or backlog item if polish), then open a **fix PR** on `main` that cites the failing step. Re-run the relevant section after the fix merges.

### Merge checklist (edit as PRs land)

Mark each row when merged to `main`:

| PR | Kind | Risk | Touch points |
| --- | --- | --- | --- |
| #519 | Tier B (architecture) | low | `ui/components/` (loading, feedback, dropdown dismiss) |
| #520 | Tier C | medium | `shopping/weekly_grocery_build`, `grocery_list_edits`; UI session in `ui/grocery_flow` |
| #522 | Tier D | medium-high | `integrations/notion/*` + import shims |
| #523 | Tier E | low-medium | feedback → `integrations/`, `recipes/prompts`, removed `lib/` |
| #525 | tidy | low | `paths.py`, test `ui_source` / `repo_paths`, deduped constants |
| #526 | tidy | low | guards (CLI, NYT, feedback), `pyproject` Ruff rules, `docs/architecture/path-anchors.md` |
| [#527](https://github.com/rachelgramlich/grocery-wizard/pull/527) | tidy | low-medium | Ruff **BLE**, `integrations/notion_io_errors.py`, narrowed Notion/HTTP `except` at boundaries, UI cache/views |
| *(add rows)* | tidy | — | next PR stacked on #527 |

**UAT starts when:** every checked-in row above is merged (or you explicitly drop a row and note why in a comment on this issue).

---

## Expected behavior & manual test hints

### 0. Preconditions

- [ ] All PRs in the **merge checklist** are on `main`.
- [ ] `git pull origin main` and note SHA.
- [ ] `just setup` if deps or `pyproject.toml` changed (#526+).
- [ ] Record date, machine, and Notion mode: **prod** (`.env`) vs **CI** (`NOTION_CI_*` / `GROCERY_WIZARD_NOTION_CI_LIVE=1`).

### 1. Automated gate (required)

On **`main`**:

```bash
just ci
```

Or explicitly:

```bash
just check          # ruff + pytest (includes holistic smoke)
just golden-grocery # weekly export regressions (Tier C + tidy paths)
just smoke-ui       # holistic AppTest smoke
```

| Step | Pass criterion |
| --- | --- |
| `just ci` / `just check` | Exit 0 |
| `just golden-grocery` | All golden weeks match; any diff → bug or fix PR |
| `just smoke-ui` | Holistic smoke green (mocked Notion) |

**On failure:** failing test name + owning area (`ui/`, `shopping/`, `integrations/`, `paths`, tidy PR).

**Tidy-focused pytest spot checks** (if golden/smoke look wrong after #525–#527):

```bash
uv run pytest tests/src/grocery_wizard/ui/test_app_notion_clear_imports.py -q
uv run pytest tests/src/grocery_wizard/ui/test_notion_cache.py -q
uv run pytest tests/src/grocery_wizard/ui/test_feedback_ui.py -q
uv run pytest tests/src/grocery_wizard/integrations/test_nyt_cooking.py -q
uv run pytest tests/src/grocery_wizard/ui/test_browse_logic.py -q
```

### 2. Import / path sanity (required, quick)

```bash
PYTHONPATH=src uv run python -c "
from grocery_wizard import paths
from grocery_wizard.paths import REPO_ROOT, UI_APP_PATH
from grocery_wizard.integrations.notion import NotionRecipesDB, Recipe
from grocery_wizard.integrations.notion_table import NotionDatabase
from grocery_wizard.integrations.feedback_submit import submit_feedback
from grocery_wizard.shopping.weekly_grocery_build import build_grocery_result_payload
from grocery_wizard.ui.components.loading import loading_indicator
assert paths.PACKAGE_ROOT.name == 'grocery_wizard'
print('import ok', UI_APP_PATH)
"
rg 'grocery_wizard\\.lib' src tests || true   # expect no product imports under src/
```

**Pass:** `import ok` and paths resolve; no stray `grocery_wizard.lib` under `src/`.

Optional doc skim: `docs/architecture/path-anchors.md` (#526).

### 3. Browser smoke — every primary page (required when Notion preflight succeeds)

**Preflight** (prod):

```bash
test -n "${NOTION_API_KEY:-}" && PYTHONPATH=src uv run python -c "from grocery_wizard.config import load_config; load_config(); print('notion ok')"
```

**Preflight** (Cloud / CI): `AGENTS.md`, `docs/operations/notion-ci-setup.md`.

```bash
just grocery-ui
```

Global: **Refresh**, **Feedback**, loading banner, dropdown dismiss (Tier B + tidy UI paths).

| Page | Focus |
| --- | --- |
| Create weekly plan | Saved-plan list; meals; grocery build through review → final list (Tier C) |
| Browse recipes | Grid, filters, empty state copy (#525 dedupe) |
| Add Recipe | URL / manual / NYT block (#526 NYT credentials path) |
| Pantry & recurring | Lists after refresh (Notion Tier D) |
| Recipe maintenance | Opens clean |

**Weekly happy path:** pre-build → recipe review → final list → copy controls. Undo test writes to Notion.

### 4. In-app feedback (required — Tier E + #526 guards)

1. **Send feedback** on `weekly` and `add`.
2. **Pass:** no traceback; success flash. Optional: GitHub inbox if token configured.

### 5. Optional deeper checks

- Live read-only holistic: `uv run pytest tests/src/grocery_wizard/ui/test_holistic_ui_smoke_apptest.py -k "live and read_only" -q`
- NYT sync UI on Add Recipe: block renders (full sync optional)
- Dev jumps (`GROCERY_WIZARD_DEV_UI=1`): Dev → Final list / golden path

### 6. Sign-off checklist

Post on this issue when done:

- [ ] Merge checklist complete on `main`
- [ ] `just ci` (or `just check` + `golden-grocery` + `smoke-ui`)
- [ ] Import / path sanity script
- [ ] Browser: all five primary pages (+ weekly grocery path)
- [ ] Feedback ×2 surfaces
- [ ] **Holistic smoke:** ran / skipped — reason
- [ ] **Browser smoke:** ran / skipped — reason
- [ ] Fix PRs opened for any failures (link below)

**Fix PRs (if any):** _none yet — add links_

### Area

**ui** (primary) + **other** (integrations, paths, tidy)

---

**Related:** implementation issues #515–#518; tidy work via `/tidy-project`. This issue is **human UAT after the full merge train**, not a single PR.