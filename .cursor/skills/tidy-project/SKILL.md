---
name: tidy-project
description: Scan the whole grocery-wizard repo and open one or more structure-only tidy PRs (no behavior changes). Invoke explicitly with /tidy-project in Agent chat.
disable-model-invocation: true
---

# Tidy project

**Repo-wide structure-only pass.** Scan the project, apply *Tidy First?* tidyings, and open **one or more PRs** that contain **no behavior changes**.

For tidying **while implementing a feature**, use the **`tidy-first`** skill — not this skill.

## Outcome

- PR title pattern: `chore(tidy): <area or theme>` (structure only).
- PRs **ready for review** unless the user asks for draft.
- Every PR passes `just check` on touched paths.
- PR description lists: areas scanned, tidyings applied, files touched, explicit **“No behavior change”** statement.

## Rules (same as tidy-first skill)

1. **S only** — no feature fixes, no bug fixes, no test expectation changes unless tests only mirrored dead code removal with identical behavior.
2. **Separate PRs** from any in-flight feature work; branch from latest `main`.
3. **Split PRs** when diff grows large or areas are unrelated (e.g. `src/grocery_wizard/ui` vs other areas).
4. **Small commits** inside each PR; one theme per commit when practical.

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

Use `uv run ruff check` and test failures as hints; do not “fix” behavior to green tests.

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

### 7. Report

Summarize PR links, themes per PR, and anything **not** tidied (risk of behavior drift, needs feature work first).
