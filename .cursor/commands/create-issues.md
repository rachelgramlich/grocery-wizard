# Create GitHub issue(s)

**Scope: issue capture only.** Turn one or more user notes into the right number of GitHub issues, then stop. Implementation is **`/work-on-issue <number>`** later.

## Use This Mac (local agent)

**Before creating issues**, tell the user:

> Issue creation works best on **This Mac** (local agent). If this chat is a **Cloud** agent, switch to **This Mac** and run **`/create-issues`** again.

- If Cloud (or unsure), **stop after the reminder** until the user confirms This Mac.
- Requires **`gh`** authenticated for this repo.

## Do not implement in this turn

- Do not open PRs, branches, or code changes unless the user asks **after** issues exist.
- Do not run **`/work-on-issue`** in this turn.

## Planning rules (you apply these in chat)

1. **Kind:** **bug** if the note describes broken/incorrect behavior, crashes, or regressions; otherwise **enhancement** backlog.
2. **Area** (`gw-area-*` label): infer from keywords — **ui** (Streamlit, buttons, layout), **parser** (ingredients, normalize), **shopping** (grocery list, pantry, aisles), **recipes** (Notion recipes, NYT, meal plan), **cli** (terminal, slash commands), **other** when unclear.
3. **Grouping:** Merge notes that share **kind + area** and can ship in one PR. Split when area differs or bug vs feature differs.
4. **Architecture audit follow-ups:** Add label **`audit`** (and pass `--label audit` on create) when filing from **`/architecture-review` Phase B**.

Valid areas match the table in `.cursor/commands/work-on-issue.md`.

## Your task

1. Collect **all** notes the user gave. Ask for missing detail only if you cannot classify or group.

2. **Explain the plan** in plain language (count, merge/split rationale, bug vs backlog).

3. If the user agrees (or gave a clear “create them”), create issues with **`gh`**:

**Enhancement backlog** (use repo template fields; add labels):

```bash
gh issue create \
  --title "Your short title" \
  --body "$(cat <<'EOF'
### Description

…

### Expected behavior & manual test hints

…

### Area

ui
EOF
)" \
  --label grocery-wizard --label gw-area-ui
```

Add `--label audit` for architecture audit items.

**Bugs** — prefer the **`bug_report.yml`** template interactively, or mirror its sections in `--body` and add `--label bug` (and `--label audit` when applicable).

4. Reply with issue numbers, URLs, and kind. Note **`/work-on-issue <n>`** for backlog items; bugs use the same command for the fix brief.

## Overrides

If auto-planning is wrong, adjust titles/bodies/labels before `gh issue create`, or edit the issue in GitHub after creation.
