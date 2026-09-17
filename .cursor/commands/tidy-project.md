# Tidy project

Apply **Kent Beck — *Tidy First?*** on the codebase area the user names (or the whole repo). **Structure only** in this pass unless the user also asked for behavior changes.

## Core rules

1. **One hat:** structure change (**S**) or behavior change (**B**) — never both in the same commit.
2. **Tidyings preserve behavior.** If observable output changes, that is **B**, not tidying.
3. **Separate commits:** tidy first (or tidy-only PR), then behavior in a follow-up commit/PR.
4. **Small steps:** prefer several tiny tidyings over one large refactor.
5. **Reversible:** if a tidying does not read better, revert it.

## When to tidy first

Ask: *What **S** makes the next **B** cheaper?*

| Situation | Action |
| --- | --- |
| Mess blocks the feature you are about to add | Tidy first, then **B** |
| Tidying does not help this change | **B** now; optional tidy after |
| Only cleaning up, no feature | Tidying-only commits/PR |
| S and B already mixed | Untangle (rebase/split commits), ship tangled only if user insists, or redo |

Do **not** dogmatically tidy everything upfront or refuse all tidying.

## How to tidy (workflow)

1. **Scope** — Files or module the user pointed at; read surrounding style first.
2. **Goal** — One sentence: what behavior change is coming (if any), or “readability/coupling only.”
3. **Pick tidyings** — From the catalog below; chain 1–3 related moves max per commit.
4. **Apply** — Run `just check` / `ruff` on touched Python; no new features in this commit.
5. **Commit message** — Prefix e.g. `chore(tidy): …` or `refactor: … (structure only)`; state technique if helpful.
6. **Handoff** — If **B** was deferred, list what is ready for the next commit/PR.

## Tidying catalog (pick what fits)

| Tidying | Do this |
| --- | --- |
| **Guard clause** | Early return on invalid/edge cases; flatten nested `if`. |
| **Delete dead code** | Remove unused vars, commented-out code, unreachable paths. |
| **Normalize symmetries** | Same kind of check/logic expressed the same way everywhere. |
| **Explaining variable / constant** | Name a subexpression or magic number after its meaning. |
| **Explicit parameters** | Replace opaque dict bags with named params where call sites clarify intent. |
| **Chunk statements** | Blank lines between logical groups (balance screen space). |
| **Extract helper** | Name a chunk of logic; keep helpers private unless shared. |
| **Reading order** | Order functions in a file for top-down reading. |
| **Cohesion order** | Keep elements that change together close together. |
| **One pile** | Temporarily inline scattered logic to understand it; then re-split cleanly. |
| **Comments** | Add only non-obvious intent; delete comments that duplicate the code. |
| **New interface, old impl** | Introduce the API you wish existed; delegate to current code until **B** lands. |

Practice examples (optional): `rg-playground` → `src/python_practice/tidy_first/`.

## Review bar

- **Structure PR / commit:** light review — diff should be easy to undo.
- **Behavior PR / commit:** tests, manual verification, full review.

## Your task

1. Confirm scope with the user if unclear.
2. Execute tidyings per workflow above; **do not** mix **B** unless explicitly requested.
3. Report: files touched, tidyings used, suggested next **B** step (if any).
