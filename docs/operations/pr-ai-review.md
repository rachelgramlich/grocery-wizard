# AI pull request review (Bugbot + Cloud agents)

This repo supports **one automatic Bugbot review per PR** (not on every commit) and a **PR listen loop** so Cloud agents that open PRs can react to review comments without you babysitting the chat.

## What lives in the repo

| File | Purpose |
| --- | --- |
| [`.cursor/config/bugbot.yaml`](../../.cursor/config/bugbot.yaml) | `oncePerPr`, no draft reviews, autofix off |
| [`.cursor/BUGBOT.md`](../../.cursor/BUGBOT.md) | Project review rules for Bugbot |
| [`AGENTS.md`](../../AGENTS.md) | Mandatory PR + CI subscriptions and review follow-up |

Bugbot reads `bugbot.yaml` from the **base branch** (usually `main`). Merge config changes before they apply to other PRs.

## One-time Cursor dashboard setup

Do this once per team (repo owner / admin).

### 1. Enable Bugbot on GitHub

1. Open [Cursor → Automations → Bugbot](https://cursor.com/dashboard?tab=bugbot) (or **Integrations** → GitHub, then Bugbot).
2. Connect **GitHub** if needed.
3. Turn **Bugbot on** for **`rachelgramlich/grocery-wizard`**.
4. Align team defaults with the repo file:
   - **Run only once per PR** (same as `frequency: oncePerPr`).
   - **Draft PRs:** off unless you want early draft reviews (repo file has `drafts: false`).
5. For **Cloud agent PRs** (`cursor[bot]`): if personal “only when mentioned” does not apply to bot PRs, rely on repo `oncePerPr` + opening PRs **ready for review** (not draft) so you get a single review at open.

Docs: [Bugbot](https://cursor.com/docs/bugbot).

### 2. Optional: PR Routing & Approval

Use [PR Routing & Approval](https://cursor.com/docs/approval-agents) only if you want auto-approve or reviewer routing.

Recommended triggers for your “not every commit” goal:

- **PR opened** — on (non-draft create or **ready for review**).
- **PR pushed / updated** — **off** unless you want re-approval after each push.

Enable **Bugbot review context** if the approval agent should wait for Bugbot.

### 3. Branch protection (optional)

Require check **`Cursor Bugbot`** before merge if you want review always attempted. Findings often use conclusion `neutral`; use fail-on-unresolved only if your org enables it.

## Cloud agent behavior (automatic)

When a Cloud agent **creates or updates a PR** for this repo, [`AGENTS.md`](../../AGENTS.md) requires:

1. **`cursor-subscriptions-subscribe_github_ci`** on the branch after push.
2. **`cursor-subscriptions-subscribe_github_pr`** on that PR URL (same chat).
3. On wake (CI green or new review activity): fix real issues, run **`just check`** (and UI smokes per issue), push, **reply** on threads, **`resolve_comment`** when fixed, re-subscribe until merge/close.

Bugbot will **not** re-review every push (`oncePerPr`). Humans or agents can still comment `bugbot run` for an extra pass.

## Manual re-review

On the PR:

```text
bugbot run
```

or

```text
cursor review
```

Use `bugbot run verbose=true` to see which rules ran.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No Bugbot on new PR | Bugbot enabled for repo in dashboard; PR not draft if `drafts: false`; base branch includes `bugbot.yaml`. |
| Review on every commit | Dashboard “once per PR” + repo `frequency: oncePerPr`; turn off incremental approval agents’ **pushed** trigger. |
| Agent never fixes comments | Agent chat must subscribe to PR (`Listening` / **Triggers** pill in Cursor). |
| Bot PR reviewed when you wanted manual | Open agent PRs as draft until ready, or use dashboard manual-only (API: `manualTriggerOnly`) — manual `bugbot run` still works. |