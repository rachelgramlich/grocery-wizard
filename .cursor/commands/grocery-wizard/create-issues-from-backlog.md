---
name: create-issues-from-backlog
description: Triage GitHub user-feedback-inbox issues → draft backlog plan → create after user approval
---

# Create GitHub issues from feedback inbox

**Scope: triage only.** List open issues labeled **`user-feedback-inbox`** (filed by Streamlit **Send feedback**), propose promoted backlog issues in chat, create them only after the user approves. Do not run **`/work-on-issue`** in this turn unless the user asks separately.

For full inbox cleanup workflow, prefer **`/triage-feedback-inbox`** when [#355](https://github.com/rachelgramlich/grocery-wizard/issues/355) ships.

## Use This Mac (local agent)

**Before creating backlog issues on GitHub**, tell the user:

> Issue creation works best on **This Mac** (local agent). If this chat is a **Cloud** agent, you may still **list inbox issues and post the draft plan**; switch to **This Mac** for **`gh issue create`** unless the user explicitly says to create from Cloud.

Requires **`gh`** authenticated for this repo when creating issues.

## Do not implement in this turn

- Do not open PRs, branches, or application code changes unless the user asks **after** issues exist.
- Do not run **`/work-on-issue`** in this turn.

## Inbox source (GitHub)

**Who writes entries:** **Send feedback** in the app creates GitHub issues with label **`user-feedback-inbox`**.

| Item | Value |
| --- | --- |
| **List** | `gh issue list --label user-feedback-inbox --state open --json number,title,body,labels,createdAt` |
| **Promote** | New issues with label `grocery-wizard` (+ area labels); close or relabel inbox issue when done |

If the inbox is **empty**, say so and stop after suggesting a test submission via `just grocery-ui` (requires `GITHUB_FEEDBACK_TOKEN` in `.streamlit/secrets.toml` or env).

## Workflow

1. **List** open `user-feedback-inbox` issues (command above).
2. **Draft** one or more backlog issues in chat (group by area; use repo issue template sections).
3. **Wait for user approval** before `gh issue create`.
4. After create: **close** the inbox issue(s) or remove `user-feedback-inbox` and add `grocery-wizard` per team convention ([#355](https://github.com/rachelgramlich/grocery-wizard/issues/355)).

## Labels and areas

| Label | When |
| --- | --- |
| `grocery-wizard` | Approved backlog enhancement |
| `bug` | Confirmed defect |
| `gw-area-*` | From issue body / surface hint |

See **`AGENTS.md`** for area → files.
