---
name: app-review
description: Hands-on Streamlit app review → findings report → grouped GitHub issues via gh
---

# App review (UAT through issue filing)

**Scope:** Manually exercise the **Grocery Wizard Streamlit UI** end-to-end, return a structured findings report, and (when the user asks) file grouped GitHub issues. **Do not implement fixes** in this turn unless the user explicitly asks after issues exist.

**Chained workflow:** Findings capture here → issue creation follows **`.cursor/commands/create-issues.md`** (same bug/backlog rules, labels, and `gh` usage).

## Prerequisites

- **This Mac (local agent)** for browser UAT and **`gh issue create`**. If the chat is **Cloud**, run the review when the browser can reach the app; **stop before creating issues** until the user switches to **This Mac** (same reminder as **`/create-issues`**).
- Repo root workspace; **`.env`** with Notion (and NYT if testing sync).
- **`gh`** authenticated for this repo when filing issues.
- Read **`.cursor/skills/developing-with-streamlit/SKILL.md`** before editing or interpreting Streamlit behavior (this command is test-only, but the skill applies to UI navigation expectations).

## Do not in this turn

- Open PRs, branches, or product code changes (except adding/updating this command when maintaining the workflow).
- Run **`/work-on-issue`** unless the user asks **after** issues are filed.
- Run a full NYT sync **without** dry run unless the user explicitly requests it (avoid mass Notion writes during review).

## App surfaces to cover

Use **`src/grocery_wizard/ui/app.py`** entry and section tabs from **`src/grocery_wizard/ui/tabs.py`**:

| Tab | Minimum path |
| --- | --- |
| **Weekly recipe generation** | Start modes (prefer **Dev mode** for no Notion saves unless user wants save flows) → meal count → **Build my plan** → **Create grocery list** → per-recipe review (if shown) → final list (copy/download, pantry adjust expanders). Optionally exercise **Start from a saved list** if user wants save flows. |
| **Add Recipe** | Empty URL validation → **Start blank recipe** (expand manual section if needed) → skim NYT sync UI (dry run default; do not live-sync unless asked). |
| **Pantry & recurring** | List loads; add/remove forms reachable (do not require persisting test data unless user OK). |
| **Global** | **Refresh from Notion**; tab switching after long weekly scroll; note load/blank states on first open. |

Start the app with **`just grocery-ui`** (or confirm an existing listener on port **8501**). Use **browser automation** (e.g. Cursor browser MCP) for hands-on UAT—not code-only guesses.

## Findings report (required before issues)

Deliver a single report with four sections. Each bullet should be **specific** (what you did, what happened). Prefer severity within the category (e.g. “blocks happy path” vs “polish”).

1. **Slow** — cold start, reruns, multi-second buttons, huge dropdowns/lists, missing loading feedback.
2. **Unintuitive** — copy, layout, hidden steps, dev-only UI visible to users, navigation friction.
3. **Broken** — incorrect data, tab/content mismatch, missing items, crashes, errors.
4. **Other improvements / enhancements** — UX polish, performance ideas, accessibility, dedupe with open issues if you know them.

Note **what worked** briefly so the user knows coverage was real.

## Issue filing phase (when user asks)

After the report, if the user wants issues (e.g. “create issues for all of them”, “file these”, **`/create-issues`**-style approval):

1. **Plan in chat:** Count of issues, **merge/split** rationale (same **kind + area** → one issue when one PR could ship it), bug vs enhancement.
2. Follow **`.cursor/commands/create-issues.md`** exactly for:
   - **bug** + `bug` label vs **enhancement** + `grocery-wizard` + `grocery-wizard-enhancement` + `gw-area-*`
   - Issue bodies (bug sections vs enhancement Description / Expected behavior & manual test hints / Area)
3. Create issues with **`gh issue create`** (HEREDOC bodies).
4. Reply with **numbers, URLs, kind**, and suggest **`/work-on-issue N`** for fixes (bugs first when they affect correctness).

Reference the review report in issue bodies (repro steps, recipe names used, tab names) so future agents can re-verify.

## Your task

1. Ensure the UI is running (`just grocery-ui` or existing process on **8501**).
2. Exercise **all three tabs** and the **weekly flow through a grocery list** (Dev mode unless user specifies otherwise).
3. Post the **four-category findings report** (+ what worked).
4. If the user requested issue creation in the same message or confirms after the report, execute the **Issue filing phase** above without re-asking unless grouping is ambiguous.
