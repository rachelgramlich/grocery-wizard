---
name: triage-feedback-inbox
description: Triage GitHub user-feedback-inbox issues → draft backlog plan → promote after user approval
---

# Triage feedback inbox (GitHub → backlog)

**Scope: triage only.** List open issues labeled **`user-feedback-inbox`** (from Streamlit **Send feedback**), draft a promotion plan in chat (merge, split, rewrite, areas), then create or update real backlog issues **only after the user approves**. Do not run **`/work-on-issue`** in this turn unless the user asks separately.

**Related:** **`/create-issues-from-backlog`** is a short pointer to this command. Raw feedback pipeline: #354 (deploy + PAT). Local dev file inbox: #240.

## Use This Mac (local agent)

**Before creating or closing issues on GitHub**, tell the user:

> Promotion works best on **This Mac** (local agent). If this chat is a **Cloud** agent, you may still **list inbox issues and post the draft plan**; switch to **This Mac** for **`gh issue create`**, comments, close, and label edits unless the user explicitly says to run those from Cloud.

Requires **`gh`** authenticated for this repo when mutating GitHub.

## Do not implement in this turn

- Do not open PRs, branches, or application code changes unless the user asks **after** backlog issues exist.
- Do not run **`/work-on-issue`** in this turn.

## Inbox source (GitHub)

| Item | Value |
| --- | --- |
| **List** | `gh issue list --label user-feedback-inbox --state open --json number,title,body,labels,createdAt,url` |
| **One issue** | `gh issue view <n> --json number,title,body,labels,comments,url` |
| **Search backlog dupes** | `gh issue list --label grocery-wizard --state open --search "<keywords>" --limit 20` |

If the inbox is **empty**, say so and stop after suggesting a test submission via **`just grocery-ui`** (requires **`GITHUB_FEEDBACK_TOKEN`** in `.streamlit/secrets.toml` or env).

## Planning rules (apply in chat before any `gh` writes)

Read **`AGENTS.md`** for **backlog label**, **bug label**, **area labels**, and issue body sections.

1. **Kind:** **`bug`** if broken/incorrect behavior, crashes, or regressions; otherwise **enhancement** → **`grocery-wizard`** (+ **`gw-area-*`**).
2. **Area:** Infer from body text, page names, or UI hints; map to **`gw-area-ui`**, **`gw-area-parser`**, **`gw-area-shopping`**, **`gw-area-recipes`**, **`gw-area-cli`**, or **`gw-area-other`**. When unclear, say so in the draft plan.
3. **Merge:** Combine inbox issues that describe the same **kind + area** and could ship in one PR. Note merged source issue numbers in the promoted body.
4. **Split:** Separate when **area** differs, **bug vs enhancement** differs, or scope is too large for one issue.
5. **Rewrite titles:** Backlog titles should be actionable (“Fix …”, “Add …”), not raw user phrasing.
6. **Existing backlog:** If an open **`grocery-wizard`** issue already covers the feedback, prefer **updating** that issue (comment + link) instead of duplicating.

## Draft plan (required before promotion)

Post a structured plan the user can approve or edit:

- **Inbox issues reviewed:** `#n` titles (links).
- **Proposed backlog issues:** For each: title, kind (bug vs enhancement), labels, which inbox `#` map to it, merge/split notes.
- **Skipped / needs info:** Anything too vague to promote without user input.
- **Dupes of open backlog:** `#existing` — comment-only vs close inbox.

Use repo template sections in proposed bodies:

- **Enhancement:** `### Description`, `### Expected behavior & manual test hints`, `### Area`
- **Bug:** follow **`/create-issues`** / **`AGENTS.md`** bug body conventions

Include a **`### Original feedback`** subsection (or blockquote) preserving submitter text verbatim from each inbox issue (issue #, date if helpful).

## Promotion phase (only after user approval)

1. **Ensure label `promoted` exists** (create once if missing):

```bash
gh label list --json name --jq 'map(.name) | index("promoted")' | grep -q null && \
  gh label create promoted --description "Inbox feedback promoted to backlog" --color "C5DEF5"
```

2. **For each approved backlog item:**

   - **New issue:** `gh issue create` with `--title`, `--body` (HEREDOC), and labels (`grocery-wizard` or `bug`, plus `gw-area-*`).
   - **Existing issue:** `gh issue comment <n> --body "…"` with original feedback and links to inbox source(s).

3. **For each consumed inbox issue `#n`:**

   - Comment linking promoted backlog issue(s): `Promoted to #<backlog>`.
   - Remove **`user-feedback-inbox`**, add **`promoted`**, **close** the inbox issue:

```bash
gh issue edit <n> --remove-label user-feedback-inbox --add-label promoted
gh issue close <n> --comment "Promoted to backlog: #<backlog> (see comment above)."
```

   - If the user asked to **keep inbox open** for audit, skip close but still add **`promoted`**, remove **`user-feedback-inbox`**, and link in comments.

4. Reply with **new/updated backlog numbers**, **URLs**, kind, and which inbox issues were closed. Suggest **`/work-on-issue <n>`** for implementation.

## Overrides

Adjust titles, bodies, labels, or close-vs-open before running `gh`. User can edit on GitHub after promotion.

## Your task

1. **List** all open **`user-feedback-inbox`** issues (`gh` JSON above).
2. **Search** for likely duplicate open backlog items when keywords are clear.
3. **Post the draft plan** (merge/split, labels, proposed titles/bodies with **Original feedback** preserved).
4. **Wait for explicit user approval** (or edits) before promotion **`gh`** commands.
5. On approval, run the **Promotion phase**, then summarize results and next steps.
