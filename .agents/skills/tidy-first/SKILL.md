---
name: tidy-first
description: Use whenever editing or refactoring application code — Kent Beck Tidy First structure-only tidyings, separate from behavior changes. Triggers refactor, cleanup, simplify, extract, guard clause, dead code, readability, messy code, tidy, tidying, split commit, structure vs behavior. Not for whole-repo scans (use /tidy-project command).
---

# Tidy First (inline while you work)

Canonical copy also lives at `.cursor/skills/tidy-first/SKILL.md` (committed). Keep both in sync when editing.

Use this skill during **normal implementation** — features, bugs, refactors the user asked for. Keep **structure (S)** and **behavior (B)** separate.

**Not in scope here:** repo-wide tidying campaigns → **`/tidy-project`** command (`.cursor/commands/tidy-project.md`).

## When to read this skill

- You are about to change code and the file is messy.
- You mixed renaming/extracting with a feature mid-edit.
- User asks to refactor, clean up, or simplify without new behavior.
- You need to decide: tidy first, tidy after, or skip.

## Non-negotiable rules

1. **One hat per commit** — S **or** B, never both.
2. **Tidyings preserve behavior** — same inputs/outputs, side effects, and UI.
3. **Small steps** — 1–3 related tidyings per commit; easy to review and revert.
4. **Match the repo** — naming, types, patterns in surrounding code (see `CONTRIBUTING.md` here).
5. **Verify** — run `just check` (or project equivalent) on touched paths.

## Automation expectations

| Layer | Enforces |
| --- | --- |
| **GitHub Actions** | `just ci` → `ruff check`, `ruff format --check`, `pytest` |
| **Pre-commit** | `ruff --fix` + `ruff-format` on commit |
| **You (inline tidy)** | **`just check`** before push; separate **S** commits from **B** |

**Repo patterns (prefer when deduping during tidy):**

- UI test paths → `tests/src/grocery_wizard/ui/ui_source.py`
- Theme static CSS path → `APP_THEME_STATIC_CSS` in `theme.py`
- Ingredient table regex → `ingredients/_patterns.py`
- CLI deprecation copy → shared constants in `cli/` shims

Details: `AGENTS.md` (Structure-only tidy), `CONTRIBUTING.md` (Automated Checks).

## Decide: tidy first?

| If… | Then… |
| --- | --- |
| Mess blocks the change you are making | Commit **S** first, then **B** |
| Tidying does not help this task | Ship **B**; optional **S** after |
| You already mixed S and B | Split commits (rebase) before opening PR |
| Tidying does not read better | Revert that tidying |

Avoid “always tidy” and “never tidy.”

## Inline workflow (with a feature or fix)

1. Name the **B** you are implementing.
2. Ask: *What **S** makes this **B** cheaper?* — if nothing, skip to **B**.
3. Apply tidyings only in files you must touch (or immediately adjacent); do not scope-creep.
4. Commit **S** with message like `chore(tidy): guard clauses in foo` (structure only).
5. Implement **B** in a follow-up commit; tests belong with **B**.
6. PR body: note if there are separate S/B commits or PRs.

## Tidying catalog

| Tidying | Do this |
| --- | --- |
| **Guard clause** | Early return; reduce nesting. |
| **Delete dead code** | Remove unused symbols, commented-out blocks. |
| **Normalize symmetries** | Same checks/logic, same shape everywhere. |
| **Explaining variable / constant** | Name intent of expressions and magic numbers. |
| **Explicit parameters** | Named args instead of opaque dicts at boundaries. |
| **Chunk statements** | Blank lines between logical groups. |
| **Extract helper** | Name a logic chunk; `_private` unless shared. |
| **Reading / cohesion order** | Order for reading; keep co-changing code together. |
| **One pile** | Inline to understand, then re-split cleanly. |
| **Comments** | Intent only; delete redundant restatements of code. |
| **New interface, old impl** | Desired API delegating to current code until **B** completes. |

## Behavior opportunities (do not mix into S)

Inline tidying stops at **S**. If you spot a **B** opportunity — bug fix, feature gap, product decision, or refactor too risky for structure-only — note it in chat or the PR, and optionally file a GitHub issue with **`gh issue create`**. Use **`.cursor/commands/create-issues.md`** planning rules (bug vs enhancement, **`gw-area-*`** labels). Never fold **B** into an **S** commit or tidy PR.

## Review expectations

- **S-only** changes: light review, should be reversible.
- **B** changes: full tests and manual verification per repo checklist.

## Optional practice reference

`rachelgramlich/rg-playground` → `src/python_practice/tidy_first/` (exercises).
