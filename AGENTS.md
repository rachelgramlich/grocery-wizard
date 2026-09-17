# Agent instructions (grocery_wizard)

## Issues (slash commands = primary UX)

| You type | Purpose |
| --- | --- |
| **`/create-issues`** | One or more notes → auto **bug vs backlog**, merge by **code area**, create GitHub issue(s) via **`gh`** |
| **`/architecture-review`** | **Phase A:** standards audit report + Ruff/CI gap analysis; **Phase B:** file **`audit`**-labeled issues (see `.cursor/commands/architecture-review.md`) |
| **`/list-enhancements`** | Open backlog (`grocery-wizard` label) via **`gh`** |
| **`/work-on-issue N`** | Load issue with **`gh issue view`**, implement using area → files table in `.cursor/commands/work-on-issue.md` |
| **`/tidy-project`** | Scan the **whole project** → structure-only tidy PR(s); no behavior changes |
| *(automatic)* **`tidy-first` skill** | While implementing work: tidy inline, **S** vs **B** in separate commits |

Slash files: `.cursor/commands/create-issues.md`, `architecture-review.md`, `list-enhancements.md`, `work-on-issue.md`, `tidy-project.md`.

Skills (committed): `.cursor/skills/tidy-first/SKILL.md`, `.cursor/skills/tidy-project/SKILL.md` (mirror under `.agents/skills/` where noted).

### Finding `/tidy-project` and `tidy-first` in Cursor

1. Open this **repo root** as the workspace (folder that contains `.cursor/`).
2. `git pull origin main` so `.cursor/commands/tidy-project.md` and `.cursor/skills/tidy-first/` exist locally.
3. **Agent** chat (not Ask-only): type `/` and filter `tidy` → **`/tidy-project`** (command) and/or **`/tidy-project`** / **`/tidy-first`** (skills on newer Cursor).
4. **Cursor Settings → Rules / Skills** (or Customize → Skills): confirm **`tidy-first`** and **`tidy-project`** appear.
5. If missing after pull: **Developer: Reload Window** or restart Cursor.

**Requires `gh`** authenticated for this repo. **Create issues on This Mac** when possible. Cloud agents should ask the user to switch before running **`/create-issues`**.

### Backlog ship checklist (enhancements)

1. PR title: `#<issue-number>: <issue title>` (truncate title if needed for GitHub limits)
2. PR template **Manual verification** + `Closes #<issue-number>`
3. Create PRs **ready for review** (not draft) unless the user asks for a draft.
4. Manual UAT: non-UI → agent runs checks and posts sign-off via **`gh pr comment`** (see `/work-on-issue`); UI → user confirms in chat, then post sign-off

Do not close backlog issues by hand — merge with `Closes #N`.

## User workflow

**Streamlit + Notion only.** Run `just grocery-ui` for recipes, meal planning, pantry, NYT recipe-box sync, and grocery lists.

After `just setup`, `.cursor/skills/developing-with-streamlit` (UI, symlink into `.venv`). **`tidy-first`** and **`tidy-project`** skills are committed under `.cursor/skills/` — no setup step.
