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
- Match existing project style.
- If files you touch are messy, read **`tidy-first`** (`.cursor/skills/tidy-first/SKILL.md`): optional **S** commit before **B**; do not mix structure and behavior in one commit.
- **UI tests:** import paths and concatenated UI source from `tests/src/grocery_wizard/ui/ui_source.py` (`APP_PATH`, `UI_ROOT`, `ui_source`, `pantry_tab_source`) — not ad-hoc `Path(...)` literals.

### 4. Smoke test (automated — not browser UAT)

Run automated smoke **before** local code review and opening the PR:

- **`just check`** (or `uv run ruff check && uv run ruff format --check && uv run pytest`).
- Any **issue-specific** checks from the issue body (CLI paths, AppTest smoke, etc.).
- **UI changes:** run whatever automated UI tests cover the surface; **§4 does not replace browser smoke UAT in §7** (AppTest/pytest alone is insufficient when the app can start).

Do not open the PR until §4 passes.

### 5. Local code review (implement fixes)

After smoke passes, review the **full branch diff vs `main`**, then **implement** warranted fixes — do not hand back a findings-only list.

**How to review (no extra Bugbot cost):**

- Prefer **Agent Review** in Cursor: **`/agent-review`** on the branch diff, or Source Control → Agent Review.
- **Depth:** **Quick** for small/trivial diffs; **Deep** for logic, security, Streamlit UX, or multi-file changes.
- Also check against the **issue acceptance criteria**, `CONTRIBUTING.md`, and the area → files table above.

**What to fix in this step:**

- Bugs, missing edge cases, weak or missing tests on touched behavior.
- Scope creep or dead code introduced in the branch.
- Style/readability issues in code you added (use **`tidy-first`** for **S** vs **B** commits when fixing).

**After fixes:**

1. Re-run **§4 Smoke test** until green.
2. If fixes were substantial, run **`/agent-review`** once more on the updated diff.
3. Only then continue to **Ship** and **Manual verification**.

### 6. Ship

- PR title: `#<issue-number>: <issue title>` (use `fix: …` prefix for bugs if clearer).
- PR body: repo template, **Manual verification**, `Closes #<issue-number>`.
- Open the PR **ready for review** (not draft) unless the user asks otherwise.

### 7. Manual verification

Fill the PR template **Manual verification** section in every case.

**No UI (library, tests, refactors, docs):** You run the steps yourself (`pytest`, `ruff check`, etc.), put what you ran in the PR table, set **Manual sign-off** to agent-verified, and post sign-off without asking the user to repeat work you already did:

```bash
gh pr comment <pr-url> --body "**Manual verification:** passed (issue #<issue-number>).

<what you ran>"
```

**Streamlit / UI (including Cloud Agents):**

**Order:** agent browser smoke (step 1) → user spot-check in chat (step 3) → `gh pr comment` sign-off (step 3). Do **not** skip step 1 because the user must confirm later. Do **not** leave **Manual sign-off: pending user verification** on the PR without running step 1 when preflight below succeeds.

**Credential preflight (Cloud Agents):** Notion/NYT values come from **Cloud Agent Secrets** (process environment). A repo-root `.env` file is optional — **missing `.env` is not “no creds.”** Before deciding env is blocked, run:

```bash
test -n "${NOTION_API_KEY:-}" && PYTHONPATH=src uv run python -c "from grocery_wizard.config import load_config; load_config(); print('notion ok')"
```

If that succeeds, browser smoke in step 1 is **required** (not optional).

1. **Smoke UAT:** Start the app (`just grocery-ui` or `uv run streamlit run src/grocery_wizard/ui/app.py`) and smoke-test in the browser via the **computerUse** subagent, covering the issue’s manual test hints from the PR **Manual verification** section.
2. **Artifacts:** Capture walkthrough evidence (screenshots/video per the walkthrough-artifacts skill); attach or link in the PR when possible.
3. **Sign-off:** Echo the PR **Manual verification** steps for the user to spot-check. Post `gh pr comment` sign-off **after the user confirms in chat** (default: agent smoke + user confirm, per `AGENTS.md`). Only skip user confirm if they explicitly delegate full UAT to the agent in chat.
4. **Env blocked** (preflight fails or the app will not start after a good-faith attempt): Fall back to automated UI coverage (`AppTest` / pytest UI tests where they exist), note the limitation in the PR **Manual verification** table, and still ask the user to confirm when they can run the UI locally.

**Smoke status (required — never silent):** In the **final chat summary** and in the PR **Manual verification** table, state explicitly which smoke ran:

| Outcome | What to tell the user / PR |
| --- | --- |
| **Browser smoke ran** | List flows exercised; link artifacts. **Manual sign-off:** pending user verification (or agent-verified if user delegated full UAT). |
| **Browser smoke skipped** | Start with **`Browser smoke: skipped`** and the **reason** (preflight failed, app failed to start, computerUse unavailable, etc.). List what ran instead (e.g. AppTest/pytest). **Do not** imply full UI UAT without browser smoke. |
| **Non-UI issue** | **`Browser smoke: N/A (non-UI)`** — §4 automated smoke only. |

If browser smoke was skipped when preflight succeeded, that is a **command violation** — fix and re-run smoke before sign-off unless the user accepts the skip in chat.

```bash
gh pr comment <pr-url> --body "**Manual verification:** passed (issue #<issue-number>).

<what you ran / smoke UAT + artifact links; or **Browser smoke: skipped** — reason>"
```

Summarize changes, **include the smoke status line**, and share the PR link.
