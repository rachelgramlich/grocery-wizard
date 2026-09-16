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
| **cli** | `src/grocery_wizard/cli/` (NYT CLI only until #180; primary UX is Streamlit) |
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

**Streamlit / UI:** Echo **Manual verification** from the PR for the user. When they confirm in chat, run the same `gh pr comment` (optional note in the body).

Summarize changes and share the PR link.
