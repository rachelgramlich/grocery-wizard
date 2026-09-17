# Work on issue

Pick up **one GitHub issue** (backlog enhancement or bug) and implement end-to-end. **You** handle the PR and UAT handoff.

## Context

- Backlog: issues with **`grocery-wizard`** label (list via **`/list-enhancements`**).
- Bugs: **`bug`** label (not in backlog list; user gives the issue #).

## Area → files (read first)

| Area | Files |
| --- | --- |
| **ui** | `src/grocery_wizard/ui/app.py` |
| **parser** | `src/grocery_wizard/ingredients/normalize.py`, `src/grocery_wizard/ingredients/_patterns.py` |
| **shopping** | `src/grocery_wizard/shopping/grocery_list.py`, `src/grocery_wizard/shopping/pantry.py` |
| **recipes** | `src/grocery_wizard/recipes/add_recipe.py`, `src/grocery_wizard/recipes/scraper.py` |
| **cli** | `src/grocery_wizard/cli/` (deprecation shims; product is Streamlit) |
| **other** | *(no default file map — skim issue + grep)* |

Area usually comes from label `gw-area-<name>` or `### Area` in the issue body.

## Your task

### 1. Resolve issue number

- If the user typed a number (e.g. `/work-on-issue 96`), use it.
- Otherwise run **`/list-enhancements`**, show open backlog items, and ask which # to use.

### 2. Load full instructions

```bash
gh issue view <issue-number> --json title,body,labels,url
```

Build a branch name: `cursor/<slug>-21af` where `<slug>` is a lowercase hyphenated slice of the title (max ~40 chars, alphanumeric only).

Follow the issue title/body plus this command file for ship steps.

### 3. Implement

- `git fetch origin main` and create branch `cursor/<slug>-21af` off `main`.
- Match existing project style; `uv run ruff check` on touched Python.

### 4. Ship

- PR title: `#<issue-number>: <issue title>` (use `fix: …` prefix for bugs if clearer).
- PR body: repo template, **Manual verification**, `Closes #<issue-number>`.
- Open the PR **ready for review** (not draft) unless the user asks otherwise.

### 5. Manual verification

Fill the PR template **Manual verification** section in every case.

**No UI (library, tests, refactors, docs):** You run the steps yourself (`pytest`, `ruff check`, etc.), put what you ran in the PR table, set **Manual sign-off** to agent-verified, and post sign-off without asking the user to repeat work you already did:

```bash
gh pr comment <pr-url> --body "**Manual verification:** passed (issue #<issue-number>).

<what you ran>"
```

**Streamlit / UI (including Cloud Agents):**

1. **Smoke UAT:** When credentials/env allow, run the app (`just grocery-ui` or `uv run streamlit run …`) and smoke-test in the browser via the **computerUse** subagent, covering the issue’s manual test hints from the PR **Manual verification** section.
2. **Artifacts:** Capture walkthrough evidence (screenshots/video per `.cursor/skills` walkthrough-artifacts guidance); attach or link in the PR when possible.
3. **Sign-off:** Echo the PR **Manual verification** steps for the user to spot-check. Post `gh pr comment` sign-off **after the user confirms in chat** (default: agent smoke + user confirm, per `AGENTS.md`). Only skip user confirm if they explicitly delegate full UAT to the agent in chat.
4. **Env blocked** (no Notion creds, app won’t start): Fall back to automated UI coverage (`AppTest` / pytest UI tests where they exist), note the limitation in the PR **Manual verification** table, and still ask the user to confirm when they can run the UI locally.

```bash
gh pr comment <pr-url> --body "**Manual verification:** passed (issue #<issue-number>).

<what you ran / smoke UAT + artifact links>"
```

Summarize changes and share the PR link.
