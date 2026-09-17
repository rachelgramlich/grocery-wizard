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

Skills (committed): `.cursor/skills/tidy-first/SKILL.md`, `.cursor/skills/tidy-project/SKILL.md`, mirrored under `.agents/skills/tidy-first/` and `.agents/skills/tidy-project/`.

### Finding `/tidy-project` and `tidy-first` in Cursor

1. Open this **repo root** as the workspace (the folder that contains `.cursor/` — not a parent monorepo folder unless that folder is the workspace root).
2. Confirm files exist: `.cursor/commands/tidy-project.md`, `.cursor/skills/tidy-project/SKILL.md`, `.agents/skills/tidy-project/SKILL.md`.
3. Use **Agent** chat (not Ask-only). Type **`/`** then **`tidy`** — pick **`tidy-project`** (Cursor 2.4+ lists this as a **skill**; older builds also show the **command** from `.cursor/commands/`).
4. **Customize → Skills**: **`tidy-project`** and **`tidy-first`** should appear (tidy-project is explicit-invoke only).
5. **Diagnostic:** Do **`/work-on-issue`** or **`/create-issues`** appear? If **no** repo slash items appear, the workspace root or chat surface is wrong (see below). If **yes** but not tidy, run **Developer: Reload Window**.
6. **Cursor Cloud / Agents on the web:** repo `.cursor/commands/` may not populate the `/` menu; use **desktop Cursor** on this repo, or type **`/tidy-project`** anyway / attach **`@tidy-project`** if your build exposes skills there.
7. Still stuck on desktop: run **`/migrate-to-skills`** once (Cursor 2.4+) then reload; or paste “Follow `.cursor/commands/tidy-project.md`” into Agent chat.

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
