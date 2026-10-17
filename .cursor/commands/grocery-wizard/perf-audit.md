---
name: perf-audit
description: Time every Streamlit control against live Notion, rank slowest-first, research fixes, file grouped issues, then fix and re-measure
---

# Performance audit (measure → rank → research → issues → fix → re-measure)

**Scope:** Find where Grocery Wizard is slow, with numbers, for **every** page and control. Rank slowest-first, explain root causes, research the best fix patterns, file grouped GitHub issues, and (when the user asks) fix them and prove the improvement with the same harness. This command is the repeatable loop; **`docs/perf-audit.md`** holds the how-to, flag glossary, budgets, and fix playbook.

**Chained workflow:** Issue filing follows **`.cursor/commands/shared/create-issues.md`** (bug/backlog rules, labels, `AGENTS.md` templates). Fixes follow **`.cursor/commands/shared/work-on-issue.md`**.

## Prerequisites

- Repo root workspace; Notion credentials in the environment or `.env` (run the **credential preflight** from `AGENTS.md`).
- `uv sync --all-extras` done (`just setup`). **`gh`** authenticated when filing issues. On **Cloud** agents `gh` is read-only: file issues with the GitHub MCP issue tool instead (same templates and labels).
- The harness is **read-only against Notion**: reads are real, writes are intercepted and never sent, mutating non-Notion HTTP is blocked. It is safe to run on the real databases. No Notion cleanup is needed.

## Do not in this turn (unless the user asks)

- Run scenario `act` functions outside `just perf-audit` (no write stubbing: the pantry/recurring/plan buttons would write to the real Notion). Use the report's per-interaction caller list to find where requests come from.
- Run `/work-on-issue` or open fix PRs during the **measure / issue** phases.
- Run NYT sync, metadata/ingredient backfills, or feedback submit by hand: they hit external services and are marked `external` (skipped) in the catalogue; time them in the browser if the user cares.

## Phase 1: Measure

1. Preflight: `PYTHONPATH=src uv run python -c "from grocery_wizard.config import load_config; load_config(); print('notion ok')"`.
2. Run the full audit (takes several minutes: cold + warm runs, cProfile on the first warm run):

```bash
just perf-audit --profile --compare latest
```

   - First time ever: omit `--compare`. The run writes `.local/grocery_wizard/perf/perf-<stamp>.md|.json` and refreshes `latest.json` (the **baseline** for the next run).
   - Targeted re-run while fixing: `just perf-audit --only 'weekly.meals.*' --reps 3`.
   - See what exists: `just perf-audit --list` (`W` writes stubbed, `X` external/skipped).
3. Read the **Ranked** table first, then **Findings by flag**, **Notion requests per interaction**, and **Hot spots**. Definitions of every flag are in `docs/perf-audit.md`.

## Phase 2: Triage

For each scenario at or above **P2** (>= 1s warm), and every scenario with a **CACHE_MISS_WARM**, **POST_WRITE_REFETCH**, **READ_FANOUT**, **PYTHON_HEAVY** or **HEAVY_DOM** flag:

1. Name the **root cause** from the profile or Notion request list (file + function), not a guess. Use the playbook table in `docs/perf-audit.md` to map flag → likely cause → fix pattern.
2. Confirm with a one-off measurement when the cause is not obvious (time the function in isolation, count requests with `--only <id>`).
3. Check **Coverage gaps**. Any button the audit saw but no scenario covers: add a scenario in `src/grocery_wizard/dev/perf_audit/scenarios.py` (see Phase 6).
4. Group findings by **shared root cause + area** (one PR could fix them): e.g. "uncached household reads" covers pantry open, pantry search, recurring add.

## Phase 3: Research best practices

Only for **new** classes of problem (the playbook already records researched patterns). Use web search for current, authoritative guidance (Streamlit docs/forum staff answers, Notion API docs, Python docs). Prefer: caching scope and invalidation, fragment/lazy rendering, widget count, Notion request shaping, process-level memoization. Record the conclusion and source URL in the issue and add new patterns to the playbook.

## Phase 4: File issues

1. **Plan in chat first:** issue count, merge/split rationale, priority order (P0 first), expected gain per issue.
2. Create issues per **`create-issues.md`** with labels from `AGENTS.md` (enhancement: `grocery-wizard` + `gw-area-*`; plus `bug` only if behavior is wrong). Use the template sections **Description / Expected behavior & manual test hints / Area** and add:
   - **Measured:** scenario ids with warm/cold seconds and Notion request counts from the report.
   - **Root cause:** file/function.
   - **Target:** a command and number, e.g. `just perf-audit --only 'weekly.meals.idle_rerun_saved'` warm <= 1.0s and 0 warm Notion reads.
   - **Research:** pattern chosen and source URL.
3. Reply with issue numbers and URLs, ranked.

## Phase 5: Fix and re-measure (when the user asks to implement)

For each issue (highest gain first), follow **`/work-on-issue`** and **`tidy-first`** (structure vs behavior commits), plus:

1. Re-run `just perf-audit --only '<affected ids>' --reps 3 --compare latest` before opening the PR.
2. Add a **regression guard** where practical: a unit test that asserts the call pattern (e.g. cached function called once, no Notion client built per render) rather than a wall-clock number.
3. PR body: paste the **Comparison vs baseline** table and the `Browser smoke:` line required by `AGENTS.md`. UI changes need a real browser smoke (`just grocery-ui`); the harness does not measure browser paint.
4. After merge, refresh the baseline with a full `just perf-audit` so the next audit compares against reality.

## Phase 6: Tune the process (every run)

Spend a few minutes improving the loop itself, then commit it:

- New or changed controls → add/adjust scenarios (`covers=` must list the widget keys/labels).
- A finding you could not explain with the report → add the missing signal to the harness (new flag, new counter).
- A fix pattern you researched → add a row to the playbook in `docs/perf-audit.md`.
- A threshold that produced noise or missed a real problem → adjust it in `report.py` and note why in the doc.

## Your task

1. Run Phases 1 and 2 and post the **ranked list** (top 10 with seconds, flags, root cause) plus coverage gaps.
2. Do Phase 3 for any new problem class; then Phase 4 after the user approves the plan (or immediately if they said "create issues").
3. If asked to implement, do Phase 5 per issue and report **before/after** from the harness.
4. Finish with Phase 6 and state **`Browser smoke: ran` / `skipped: <reason>` / `N/A (non-UI)`** for any UI change.
