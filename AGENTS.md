# Agent instructions (grocery_wizard)

## Issues (slash commands = primary UX)

| You type | Purpose |
| --- | --- |
| **`/create-issues`** | One or more notes → auto **bug vs backlog**, merge by **code area**, create GitHub issue(s) via **`gh`** |
| **`/create-issues-from-backlog`** | Local feedback `.md` inbox → draft plan → **`gh`** create → clear inbox & archive (see `.cursor/commands/grocery-wizard/create-issues-from-backlog.md`) |
| **`/app-review`** | Hands-on Streamlit UAT → findings → optional grouped **`gh`** issues (see `.cursor/commands/grocery-wizard/app-review.md`) |
| **`/architecture-review`** | Standards audit + optional **`audit`** issues (shared: `.cursor/commands/shared/architecture-review.md`) |
| **`/list-enhancements`** | Open backlog (`grocery-wizard` label) via **`gh`** (`.cursor/commands/grocery-wizard/list-enhancements.md`) |
| **`/work-on-issue N`** | Implement one issue — area → files and UAT rules **below** + shared `.cursor/commands/shared/work-on-issue.md` |
| **`/tidy-project`** | Repo-wide structure-only tidy PR(s) (shared: `.cursor/commands/shared/tidy-project.md`) |
| **`/create-command`** | Add slash command or skill without name collisions (shared: `.cursor/commands/shared/create-command.md`) |
| **`/sync-store-aisles`** | Notion → `store_aisles.txt` keyword sync (`.cursor/commands/grocery-wizard/sync-store-aisles.md`) |
| *(automatic)* **`tidy-first` skill** | While implementing work: tidy inline, **S** vs **B** in separate commits; may file follow-up issues for **B** spotted during tidy (not in **S** commits) |

**Layout:** [rg-ai](https://github.com/rachelgramlich/rg-ai) **git submodule** at **`.cursor/rg-ai`**. Shared slash files via **`.cursor/commands/shared/`** → `.cursor/rg-ai/.cursor/commands`. Grocery-only commands in **`.cursor/commands/grocery-wizard/`**. After clone or new worktree: **`git submodule update --init --recursive`** once if `/` doesn’t list shared commands. **Command-only workflows** must not duplicate the same name under `.cursor/skills/` (see **`/create-command`**).

### Labels and areas (for `/create-issues`, `/work-on-issue`)

| Item | Value |
| --- | --- |
| **Backlog label** | `grocery-wizard` |
| **Bug label** | `bug` |
| **Area labels** | `gw-area-ui`, `gw-area-parser`, `gw-area-shopping`, `gw-area-recipes`, `gw-area-cli`, `gw-area-other` |
| **List backlog** | **`/list-enhancements`** or `gh issue list --label grocery-wizard --state open` |
| **Verify** | `just check` |

**Enhancement create example:** `gh issue create … --label grocery-wizard --label gw-area-ui` with template sections **Description**, **Expected behavior & manual test hints**, **Area**.

**Area → files (read first):**

| Area | Files |
| --- | --- |
| **ui** | `src/grocery_wizard/ui/app.py`, `docs/ui-map.md`, `src/grocery_wizard/ui/ids.py`, `src/grocery_wizard/ui/pages/` |
| **parser** | `src/grocery_wizard/ingredients/normalize.py`, `src/grocery_wizard/ingredients/_patterns.py` |
| **shopping** | `src/grocery_wizard/shopping/grocery_list.py`, `src/grocery_wizard/shopping/pantry.py` |
| **recipes** | `src/grocery_wizard/recipes/add_recipe.py`, `src/grocery_wizard/recipes/scraper.py` |
| **cli** | `src/grocery_wizard/cli/` |
| **other** | skim issue + grep |

Area from label `gw-area-<name>` or `### Area` in the issue body.

**UI vocabulary:** **page** / **block** / **control** and dot IDs (`weekly.grocery_pre_build`, `global.global.refresh`, …) — see **`docs/ui-map.md`**. Say **store aisle** for aisle grouping (not “section”).

**UI tests:** import `APP_PATH`, `UI_ROOT`, `ui_source`, `pantry_page_source` from `tests/src/grocery_wizard/ui/ui_source.py` — no ad-hoc path literals.

### Manual verification (UI issues, for `/work-on-issue`)

**Credential preflight:** `test -n "${NOTION_API_KEY:-}" && PYTHONPATH=src uv run python -c "from grocery_wizard.config import load_config; load_config(); print('notion ok')"`. Missing `.env` is OK when secrets are in the environment.

When preflight succeeds: **browser smoke** required — `just grocery-ui` (or `uv run streamlit run src/grocery_wizard/ui/app.py`), then user spot-check in chat before `gh pr comment` sign-off (unless user delegates full UAT).

**Notion UAT cleanup:** If browser smoke **writes** to Notion (status, ingredients, plans, pantry, etc.), **undo every test change before sign-off** — same UI/API path, restore prior values, and say what you reverted in chat/PR. Prefer read-only smoke when a write is not required to prove the feature.

Always state in chat and PR: **`Browser smoke: ran`**, **`Browser smoke: skipped — <reason>`**, or **`Browser smoke: N/A (non-UI)`**.

Skills (committed): `.cursor/skills/tidy-first/SKILL.md` (mirrored under `.agents/skills/tidy-first/`). Do **not** add a `tidy-project` skill — it collides with the **`/tidy-project`** command in Cursor’s `/` menu.

### Finding `/tidy-project` (command) and `tidy-first` (skill)

**`/tidy-project`** is a **slash command** from `.cursor/commands/shared/tidy-project.md`. Menu label: **`/tidy-project`** (filename). Commands load from **workspace root** `.cursor/commands/` (including subfolders).

1. Open this **repo root** as the workspace (folder that contains `.cursor/commands/`).
2. Confirm **only** the shared tidy-project command exists (no `.cursor/skills/tidy-project/`).
3. **Agent** chat (not Ask-only): type **`/`** → **`tidy-project`** (alongside `/create-issues`, `/work-on-issue`, …).
4. **Customize → Skills** shows **`tidy-first`** only; **`/tidy-project`** is under **commands**, not skills.
5. **Diagnostic:** If other repo commands appear but not **`/tidy-project`**, you likely still have a local **`tidy-project` skill** or ran **`/migrate-to-skills`** (remove `.cursor/skills/tidy-project/` and reload). If **no** repo commands appear, wrong workspace root or chat surface.
6. **Cursor Cloud / web Agents:** repo commands may not populate `/`; use **desktop Cursor** or paste the command path under `.cursor/commands/shared/`.
7. Do **not** run **`/migrate-to-skills`** on this repo if you want to keep **`/tidy-project`** as a command — migration duplicates commands as skills and breaks the menu entry.

**Requires `gh`** authenticated for this repo. **Create issues on This Mac** when possible. Cloud agents should ask the user to switch before running **`/create-issues`**.

### Backlog ship checklist (enhancements)

1. PR title: `#<issue-number>: <issue title>` (truncate title if needed for GitHub limits)
2. PR template **Manual verification** + `Closes #<issue-number>`
3. Create PRs **ready for review** (not draft) unless the user asks for a draft.
4. Manual UAT: non-UI → agent runs checks and posts sign-off via **`gh pr comment`** (see `/work-on-issue`); UI → Cloud agents **must** browser-smoke Streamlit when `NOTION_*` secrets / `load_config()` preflight succeeds (secrets do not require a `.env` file), then user confirms in chat (default) before sign-off. **Always** state **`Browser smoke: ran`**, **`Browser smoke: skipped — <reason>`**, or **`Browser smoke: N/A (non-UI)`** in chat and the PR — details in `/work-on-issue`

Do not close backlog issues by hand — merge with `Closes #N`.

## User workflow

**Streamlit + Notion only.** Run `just grocery-ui` for recipes, meal planning, pantry, NYT recipe-box sync, and grocery lists.

After `just setup`, `.cursor/skills/developing-with-streamlit` (UI, symlink into `.venv`). **`tidy-first`** skill is committed under `.cursor/skills/`; **`/tidy-project`** is shared under `.cursor/commands/shared/`.

## Structure-only tidy (agents)

- **S vs B:** Follow the **`tidy-first`** skill — structure (**S**) and behavior (**B**) in **separate commits**. Repo-wide structure passes → **`/tidy-project`** (shared command).
- **Verify before push:** `just check` runs `ruff check`, `ruff format --check`, and `pytest` on `src/` and `tests/`. Equivalent: `uv run ruff check && uv run ruff format --check && uv run pytest`.
- **CI:** GitHub Actions runs the same checks via `just ci` on every PR.
- **UI regression tests:** Import `APP_PATH`, `UI_ROOT`, `ui_source`, `pantry_page_source` from `tests/src/grocery_wizard/ui/ui_source.py` — do not copy Streamlit path literals into individual tests.
- **Dedupe constants:** One owning module for repeated paths or regex (e.g. `APP_THEME_STATIC_CSS` in `theme.py`, unicode/qty patterns in `ingredients/_patterns.py`, shared CLI deprecation strings in `cli/` shims).
