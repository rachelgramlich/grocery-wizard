---
name: tidy-first
description: "**[REQUIRED]** Use whenever editing or refactoring application code (Python, JS, etc.): apply Kent Beck *Tidy First?* — structure-only tidyings, separate from behavior changes. Triggers: refactor, cleanup, simplify, extract, rename for clarity, guard clause, dead code, readability, messy code, tidy, tidying, pre-change cleanup, split commit, structure vs behavior. Do **not** use for `/tidy-project` whole-repo scan (that command owns full-project PRs)."
---

# Tidy First (inline while you work)

Use this skill during **normal implementation** — features, bugs, refactors the user asked for. Keep **structure (S)** and **behavior (B)** separate.

**Not in scope here:** repo-wide tidying campaigns → user runs **`/tidy-project`**.

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

## Review expectations

- **S-only** changes: light review, should be reversible.
- **B** changes: full tests and manual verification per repo checklist.

## Optional practice reference

`rachelgramlich/rg-playground` → `src/python_practice/tidy_first/` (exercises).
