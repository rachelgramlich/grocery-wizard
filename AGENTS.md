# Agent instructions (grocery_wizard)

## Issues (slash commands = primary UX)

| You type | Purpose |
| --- | --- |
| **`/create-issues`** | One or more notes → auto **bug vs backlog**, merge by **code area**, create GitHub issue(s) via **`gh`** |
| **`/architecture-review`** | **Phase A:** standards audit report + Ruff/CI gap analysis; **Phase B:** file **`audit`**-labeled issues (see `.cursor/commands/architecture-review.md`) |
| **`/list-enhancements`** | Open backlog (`grocery-wizard` label) via **`gh`** |
| **`/work-on-issue N`** | Load issue with **`gh issue view`**, implement using area → files table in `.cursor/commands/work-on-issue.md` |
| **`/tidy-project`** | Scan the **whole project** → structure-only tidy PR(s); no behavior changes; may file follow-up issues via **`gh`** for deferred **B** work (see command + **`create-issues`** rules) |
| **`/create-command`** | Add a new slash **command** (or skill) without command/skill name collisions — see `.cursor/commands/create-command.md` |
| *(automatic)* **`tidy-first` skill** | While implementing work: tidy inline, **S** vs **B** in separate commits; may file follow-up issues for **B** spotted during tidy (not in **S** commits) |

Slash files: `.cursor/commands/create-issues.md`, `architecture-review.md`, `list-enhancements.md`, `work-on-issue.md`, `tidy-project.md`, `create-command.md`. **Command-only workflows** must not duplicate the same name under `.cursor/skills/` (see **`/create-command`**).

Skills (committed): `.cursor/skills/tidy-first/SKILL.md` (mirrored under `.agents/skills/tidy-first/`). Do **not** add a `tidy-project` skill — it collides with the **`/tidy-project`** command in Cursor’s `/` menu.

### Finding `/tidy-project` (command) and `tidy-first` (skill)

**`/tidy-project`** is a **slash command** from `.cursor/commands/tidy-project.md` (same pattern as `/work-on-issue`). Menu label: **`/tidy-project`** (filename), not “tidy project” with a space. Commands load only from **workspace root** `.cursor/commands/`.

1. Open this **repo root** as the workspace (folder that contains `.cursor/commands/`).
2. Confirm **only** `.cursor/commands/tidy-project.md` exists for tidy-project (no `.cursor/skills/tidy-project/`).
3. **Agent** chat (not Ask-only): type **`/`** → **`tidy-project`** (alongside `/create-issues`, `/work-on-issue`, …).
4. **Customize → Skills** shows **`tidy-first`** only; **`/tidy-project`** is under **commands**, not skills.
5. **Diagnostic:** If other repo commands appear but not **`/tidy-project`**, you likely still have a local **`tidy-project` skill** or ran **`/migrate-to-skills`** (remove `.cursor/skills/tidy-project/` and reload). If **no** repo commands appear, wrong workspace root or chat surface.
6. **Cursor Cloud / web Agents:** repo commands may not populate `/`; use **desktop Cursor** on this repo or paste “Follow `.cursor/commands/tidy-project.md`”.
7. Do **not** run **`/migrate-to-skills`** on this repo if you want to keep **`/tidy-project`** as a command — migration duplicates commands as skills and breaks the menu entry.

**Requires `gh`** authenticated for this repo. **Create issues on This Mac** when possible. Cloud agents should ask the user to switch before running **`/create-issues`**.

### Backlog ship checklist (enhancements)

1. PR title: `#<issue-number>: <issue title>` (truncate title if needed for GitHub limits)
2. PR template **Manual verification** + `Closes #<issue-number>`
3. Create PRs **ready for review** (not draft) unless the user asks for a draft.
4. Manual UAT: non-UI → agent runs checks and posts sign-off via **`gh pr comment`** (see `/work-on-issue`); UI → Cloud agents smoke-test Streamlit in the browser when feasible, then user confirms in chat (default) before sign-off — details in `/work-on-issue`

Do not close backlog issues by hand — merge with `Closes #N`.

## User workflow

**Streamlit + Notion only.** Run `just grocery-ui` for recipes, meal planning, pantry, NYT recipe-box sync, and grocery lists.

After `just setup`, `.cursor/skills/developing-with-streamlit` (UI, symlink into `.venv`). **`tidy-first`** skill is committed under `.cursor/skills/`; **`/tidy-project`** is the command in `.cursor/commands/tidy-project.md`.

## Structure-only tidy (agents)

- **S vs B:** Follow the **`tidy-first`** skill — structure (**S**) and behavior (**B**) in **separate commits**. Repo-wide structure passes → **`/tidy-project`** (`.cursor/commands/tidy-project.md`).
- **Verify before push:** `just check` runs `ruff check`, `ruff format --check`, and `pytest` on `src/` and `tests/`. Equivalent: `uv run ruff check && uv run ruff format --check && uv run pytest`.
- **CI:** GitHub Actions runs the same checks via `just ci` on every PR.
- **UI regression tests:** Import `APP_PATH`, `UI_ROOT`, `ui_source`, `pantry_tab_source` from `tests/src/grocery_wizard/ui/ui_source.py` — do not copy Streamlit path literals into individual tests.
- **Dedupe constants:** One owning module for repeated paths or regex (e.g. `APP_THEME_STATIC_CSS` in `theme.py`, unicode/qty patterns in `ingredients/_patterns.py`, shared CLI deprecation strings in `cli/` shims).
