# Architecture / standards review

**Two phases.** Default to **Phase A only** unless the user explicitly asks to file issues or implement fixes.

| Phase | Scope |
| --- | --- |
| **A — Audit** | Read codebase + standards docs, run checks, deliver a structured report (no PRs, no new issues). |
| **B — Ship** | Turn agreed findings into GitHub issues (`audit` label) and/or **`/work-on-issue N`** — only after user sign-off on Phase A. |

## Phase A — Audit (this turn)

### Standards to apply

1. **`CONTRIBUTING.md`** — human-readable coding standards (Ruff categories, typing, `__all__`, imports, pytest style, file layout). Treat this as the **review checklist** for this repo.
2. **`pyproject.toml`** — `[tool.ruff.lint]` select/ignore/per-file-ignores (what is *actually enforced* today).
3. **Reference audit:** [issue #22](https://github.com/rachelgramlich/grocery-wizard/issues/22) — example structure for a full standards pass (sections, priority order).

Skim **`src/grocery_wizard/README.md`** for domain boundaries if module placement is unclear.

### Commands to run

```bash
just lint
uv run ruff check --statistics src tests 2>/dev/null || true
uv run pytest -q --tb=no 2>/dev/null | tail -5
```

Optional (large modules / boundaries):

```bash
find src/grocery_wizard -name '*.py' ! -path '*/__pycache__/*' -exec wc -l {} + | sort -n | tail -20
```

Do **not** change production code in Phase A unless the user asked for fixes in the same message.

### Report format (required)

Use markdown with these sections:

1. **Executive summary** — 3–5 bullets: overall health, biggest risks, quick wins vs larger refactors.
2. **Findings by area** — group using `CONTRIBUTING.md` layout (`cli/`, `ingredients/`, `ui/`, etc.) or the area → files table in `.cursor/commands/work-on-issue.md`. For each finding:
   - **What** (file/symbol or pattern)
   - **Why it matters** (maintainability, bugs, consistency)
   - **Priority** (high / medium / low)
   - **Suggested fix** (concrete, sized for one PR where possible)
3. **Automation & standards gap analysis** (required) — for findings that lint/CI did *not* catch, propose **reusable guardrails**:
   - **Ruff:** rule codes to add or stop ignoring (cite current `pyproject.toml`); per-file ignores to tighten; pre-commit pin sync.
   - **Repo docs:** `CONTRIBUTING.md` sections to add or clarify.
   - **CI / hooks:** pre-commit hooks, `just check`, optional future mypy/basedpyright if typing gaps are systemic.
   - **Conventions:** `__all__`, encapsulation (no cross-module `_private` imports), module size splits, pydantic/config patterns.
   Format as a table: *Finding* | *Would be caught by* | *Proposed rule or doc change*.
4. **Suggested issue breakdown** — how many GitHub issues, merge/split rationale (same rules as `/create-issues`: one issue per **kind + code area** when shippable together).
5. **Next step** — ask whether to run **Phase B** (file issues) or pick one finding for **`/work-on-issue`**.

### Phase A exit criteria

- User has the full report and automation table.
- No issues created and no PR opened unless they opted into Phase B.

---

## Phase B — File issues (after user confirms)

**Use This Mac** for `gh` issue creation (same as `/create-issues`):

> Issue creation works best on **This Mac**. Cloud agents: ask the user to switch and re-run Phase B.

### Create audit-tagged issues

Turn each agreed finding (or merged group) into one GitHub issue. Follow **`/create-issues`** planning rules and always add the **`audit`** label (plus `grocery-wizard`, `gw-area-<area>` for enhancements, or `bug` for defects).

Include in each issue: problem, suggested fix, and **automation follow-up** (Ruff rule or CONTRIBUTING bullet) when relevant.

**Create after user agrees** — use `gh issue create` as documented in `.cursor/commands/create-issues.md` (add `--label audit` on every audit follow-up).

Enhancements get labels: `grocery-wizard`, `gw-area-<area>`, `audit`. Bugs get `bug` + `audit`.

Reply with issue URLs and remind: **`/work-on-issue <n>`** to implement.

### Phase B — Implement (optional, separate turn)

If the user wants code changes instead of (or after) issues, use **`/work-on-issue`** on an audit issue, or a dedicated branch/PR. Follow `CONTRIBUTING.md` and expand Ruff/config when the audit table proposed new rules.

---

## Overrides

- **Scope:** User may limit to one area (`ui only`, `ingredients only`) — still produce the automation table for that scope.
- **Fix in place:** If the user says “fix the high-priority items now,” treat as Phase B implementation; still list any new Ruff/doc follow-ups in the PR body.
