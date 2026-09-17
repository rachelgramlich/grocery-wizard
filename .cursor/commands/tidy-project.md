---
name: tidy-project
description: Repo-wide structure-only tidy PRs (no behavior changes). Slash command only — not a skill.
---

# Tidy project

**Repo-wide structure-only pass.** Scan the project, apply *Tidy First?* tidyings, and open **one or more PRs** that contain **no behavior changes**.

For tidying **while implementing a feature**, follow the **`tidy-first`** skill (`.cursor/skills/tidy-first/SKILL.md`) — do not use this command for that.

## Outcome

- PR title pattern: `chore(tidy): <area or theme>` (structure only).
- PRs **ready for review** unless the user asks for draft.
- Every PR passes `just check` on touched paths.
- PR description lists: areas scanned, tidyings applied, files touched, explicit **“No behavior change”** statement.

## Rules (same as skill)

1. **S only** — no feature fixes, no bug fixes, no test expectation changes unless tests only mirrored dead code removal with identical behavior.
2. **Separate PRs** from any in-flight feature work; branch from latest `main`.
3. **Split PRs** when diff grows large or areas are unrelated (e.g. `src/grocery_wizard/ui` vs `src/grocery_wizard/dev`).
4. **Small commits** inside each PR; one theme per commit when practical.
5. **Follow-up issues** — tidying stops at **S**. When scan or tidy surfaces items that need behavior fixes, product decisions, or risky refactors (not safe structure-only), file GitHub issue(s) with **`gh issue create`** instead of mixing **B** into tidy PRs. Apply planning rules from **`.cursor/commands/create-issues.md`** (bug vs enhancement, merge by area, **`gw-area-*`** labels). Cloud agents may use **`gh`** when the user allows issue creation in the tidy flow.

## Your task

### 1. Sync and branch

```bash
git fetch origin main
git checkout main && git pull origin main
git checkout -b cursor/tidy-<short-theme>-287b
```

Use a new branch per tidy PR if shipping multiple PRs sequentially.

### 2. Scan the project

Prioritize (highest mess / change friction first):

- `src/` application code (exclude generated or vendored trees if any).
- `tests/` only when tidying test **structure** (helpers, duplication) without changing what is asserted.
- Skip: lockfiles, `.venv`, third-party vendored code, unrelated docs-only churn unless user asked.

Look for: deep nesting, dead code, magic numbers, duplicated validation patterns, oversized functions that are **pure structure** to split, inconsistent symmetries, misleading names that can be clarified **without** semantic change.

Use `uv run ruff check`, `uv run ruff format --check`, and test failures as hints; do not “fix” behavior to green tests.

## Automation expectations

| Layer | Enforces |
| --- | --- |
| **GitHub Actions** | `just ci` → `ruff check`, `ruff format --check`, `pytest` |
| **Pre-commit** | `ruff --fix` + `ruff-format` on commit (local or pre-commit.ci) |
| **Agents / contributors** | Run **`just check`** before push (same Ruff + pytest as CI, no auto-fix) |

**Patterns to prefer when tidying (structure only):**

- **UI tests:** central helpers in `tests/src/grocery_wizard/ui/ui_source.py` (`APP_PATH`, `UI_ROOT`, `ui_source()`).
- **Theme CSS:** single constant `APP_THEME_STATIC_CSS` in `src/grocery_wizard/ui/theme.py`; import elsewhere.
- **Ingredient parsing:** shared regex/unicode in `src/grocery_wizard/ingredients/_patterns.py`; import from `parsed.py` / `normalize.py`, do not copy patterns.
- **CLI shims:** reuse deprecation message constants instead of duplicating strings.

### 3. Plan before editing

Produce a short plan for the user (in chat):

- Buckets by module or theme.
- Which tidyings per bucket.
- **One PR vs many PRs** (prefer ≤ ~400 lines meaningful diff per PR).

Wait for user objection only if they gave a narrow scope; if they invoked **`/tidy-project`** with no scope, proceed with the plan.

### 4. Apply tidyings

Follow the catalog in `.cursor/skills/tidy-first/SKILL.md`.

After each bucket: `just check`. Fix only issues **your tidying introduced**.

### 5. Commit and push

```bash
git add -A
git commit -m "chore(tidy): <specific theme>"
git push -u origin HEAD
```

Repeat for additional PRs from fresh branches off `main` if splitting.

### 6. Open PR(s)

Use the repo PR template. **Manual verification:**

| Step | Expected |
| --- | --- |
| `just check` | Pass |
| Smoke / UI | Unchanged behavior (same flows as before tidy) |

**Manual sign-off:** agent-verified for non-UI; UI → user confirms in chat if Streamlit paths were touched.

No `Closes #N` unless the user tied this to an issue.

### 7. File follow-up issues (optional)

After scan/tidy, for each **B** opportunity you deferred: create issue(s) via **`gh issue create`** (see rule 5 and **`.cursor/commands/create-issues.md`**). Link issue numbers in the tidy PR description or report.

### 8. Report

Summarize PR links, themes per PR, follow-up issue links (if any), and anything **not** tidied (risk of behavior drift, needs feature work first).
