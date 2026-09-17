---
name: create-command
description: Add a new repo slash command (or skill) the right way — avoid command/skill name collisions in Cursor.
---

# Create slash command (or skill)

**Scope:** Add a new **Agent workflow** to this repo so it appears when the user types **`/`** in **Agent** chat at the **repo root**. Stop after the command (and docs) are committed unless the user asks for a PR in the same turn.

## What went wrong with `/tidy-project` (read this)

We added **both**:

- `.cursor/commands/tidy-project.md` (slash **command**), and  
- `.cursor/skills/tidy-project/SKILL.md` (skill with the **same name**)

Cursor merges commands and skills into one **`/`** menu. **Identical names can hide or break the entry** — the command looked missing even after merge and pull. Fix: **one surface per name** — for `/tidy-project` we kept the **command only** and deleted the skill copies.

**Also avoid:** running **`/migrate-to-skills`** on this repo for workflows that must stay **commands**; migration duplicates them as skills and can break the menu again.

---

## Step 0 — Gather from the user

If they did not already specify:

1. **Slash name** (kebab-case, e.g. `deploy-staging` → **`/deploy-staging`**).
2. **Purpose** (one sentence).
3. **Invocation:** must the user type **`/`** to run it every time, or should the agent **auto-apply** while coding?

---

## Step 1 — Choose command vs skill

| User need | Use | Location | Appears in `/` menu as |
| --- | --- | --- | --- |
| Explicit workflow the user runs (like `/work-on-issue`, `/tidy-project`) | **Slash command** | `.cursor/commands/<name>.md` only | **`/<name>`** (filename) |
| Always-on or context-triggered guidance while editing (like inline tidy rules) | **Skill** | `.cursor/skills/<name>/SKILL.md` (+ mirror `.agents/skills/<name>/` if we mirror `tidy-first`) | **`/<name>`** or auto-applied |

**Hard rule:** If you add a **command** at `.cursor/commands/foo.md`, do **not** add `.cursor/skills/foo/` or `.agents/skills/foo/` with the same `foo`. Pick a **different** skill name if both are needed.

**Default for this repo:** Backlog and ship workflows → **commands** (see existing files in `.cursor/commands/`).

---

## Step 2 — Create the command file (when Step 1 = command)

1. Create **`.cursor/commands/<kebab-name>.md`** at the **workspace/repo root** (not under `src/`).
2. Start with optional frontmatter (helps the `/` menu):

```markdown
---
name: <kebab-name>
description: <one line for the slash menu>
---

# <Title>

**Scope:** …

## Your task
…
```

3. Match tone and structure of siblings: `create-issues.md`, `work-on-issue.md`, `tidy-project.md`.
4. Use **`## Your task`** with numbered steps the agent must follow.
5. Body is the prompt injected when the user picks **`/<kebab-name>`**.

**Do not** create a skill folder with the same name.

---

## Step 3 — Create a skill (only when Step 1 = skill)

1. **`.cursor/skills/<name>/SKILL.md`** with required frontmatter:

```markdown
---
name: <name>
description: …
---

# …
```

2. **`name`** must match the **folder** name (`<name>`).
3. For **manual-only** invoke (like a command): `disable-model-invocation: true`.
4. For **auto** while coding: omit `disable-model-invocation` or set it false; use a rich `description` with trigger words.
5. If this repo mirrors skills (see `tidy-first`): copy to **`.agents/skills/<name>/SKILL.md`** and add a one-line “keep in sync” note in both files.
6. Ensure **no** `.cursor/commands/<name>.md` exists with the same `<name>`.

---

## Step 4 — Update repo docs

1. **`AGENTS.md`** — add a row to the slash table (if command) or note under skills (if skill only).
2. **`AGENTS.md`** — append the filename to the “Slash files:” line (commands only).
3. **`README.md`** — one line under **Cursor (optional)** only if users need to discover it.

---

## Step 5 — Verify (user or agent on desktop Cursor)

1. Workspace opened at **repo root** (folder containing `.cursor/commands/`).
2. **Agent** chat (not Ask-only).
3. **Developer: Reload Window** after new files are on disk.
4. Type **`/`** → **`/<kebab-name>`** should appear **alongside** `/create-issues`, `/work-on-issue`, etc.
5. If command missing but others show: search for a **duplicate skill** with the same name and remove it.

Cloud / web Agents may not list repo commands in **`/`**; verification is on **desktop Cursor**.

---

## Step 6 — Commit

One logical commit (or command + docs commit):

```text
docs: add /create-command slash command for …
```

or

```text
docs: add /<name> slash command
```

Include only the new command/skill files and doc updates — no unrelated changes.

---

## Step 7 — Report to the user

Summarize:

- **Slash name:** `/<kebab-name>`
- **Type:** command or skill (and why)
- **Files touched**
- **Collision check:** confirmed no same-named command + skill
- **How to test:** Reload Window → **`/`** → pick the new entry

If they want a PR, follow **`/work-on-issue`** ship checklist style (ready for review unless they ask for draft).
