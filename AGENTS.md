# Agent instructions (grocery_wizard)

## Issues (slash commands = primary UX)

| You type | Purpose |
| --- | --- |
| **`/create-issues`** | One or more notes → auto **bug vs backlog**, merge by **code area**, create GitHub issue(s) via **`gh`** |
| **`/architecture-review`** | **Phase A:** standards audit report + Ruff/CI gap analysis; **Phase B:** file **`audit`**-labeled issues (see `.cursor/commands/architecture-review.md`) |
| **`/list-enhancements`** | Open backlog (`grocery-wizard` label) via **`gh`** |
| **`/work-on-issue N`** | Load issue with **`gh issue view`**, implement using area → files table in `.cursor/commands/work-on-issue.md` |

Slash files: `.cursor/commands/create-issues.md`, `architecture-review.md`, `list-enhancements.md`, `work-on-issue.md`.

**Requires `gh`** authenticated for this repo. **Create issues on This Mac** when possible. Cloud agents should ask the user to switch before running **`/create-issues`**.

### Backlog ship checklist (enhancements)

1. PR title: `#<issue-number>: <issue title>` (truncate title if needed for GitHub limits)
2. PR template **Manual verification** + `Closes #<issue-number>`
3. Create PRs **ready for review** (not draft) unless the user asks for a draft.
4. Manual UAT: non-UI → agent runs checks and posts sign-off via **`gh pr comment`** (see `/work-on-issue`); UI → user confirms in chat, then post sign-off

Do not close backlog issues by hand — merge with `Closes #N`.

## User workflow

**Streamlit + Notion only.** Run `just grocery-ui` for recipes, meal planning, pantry, and grocery lists.

**Temporary CLI (until [#180](https://github.com/rachelgramlich/grocery-wizard/issues/180)):** NYT Cooking sync only:

```bash
uv run python -m src.grocery_wizard nyt sync
```

After `just setup`, Streamlit’s `developing-with-streamlit` skill is under `.cursor/skills/` for UI work.
