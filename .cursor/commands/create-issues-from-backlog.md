---
name: create-issues-from-backlog
description: Triage local UI feedback backlog → draft GitHub issue plan → create after user approval
---

# Create GitHub issues from local feedback backlog

**Scope: issue capture only.** Read the **gitignored** feedback backlog written by the Streamlit UI (#240), propose GitHub issues in chat, create them only after the user approves. Do not run **`/work-on-issue`** in this turn unless the user asks separately.

## Use This Mac (local agent)

**Before creating issues on GitHub**, tell the user:

> Issue creation works best on **This Mac** (local agent). If this chat is a **Cloud** agent, you may still **scan the backlog and post the draft plan**; switch to **This Mac** for **`gh issue create`** unless the user explicitly says to create from Cloud.

Requires **`gh`** authenticated for this repo when creating issues.

## Do not implement in this turn

- Do not open PRs, branches, or application code changes unless the user asks **after** issues exist.
- Do not run **`/work-on-issue`** in this turn.

## Backlog file (local, gitignored)

**Who writes it:** the Streamlit **Send feedback** control in issue **#240** appends each submission. **This slash command only reads and archives** — it does not implement the UI or create the file on first use.

| Item | Value |
| --- | --- |
| **Path** | `.local/grocery_wizard/feedback_backlog.md` (repo root; same tree as `DATA_DIR` in `src/grocery_wizard/config/__init__.py`) |
| **Archive** | `.local/grocery_wizard/feedback_backlog.archived.md` (append-only; processed entries) |
| **Format** | **Markdown**, UTF-8, **append-only** blocks (human-readable in any editor) |

Each entry is one block, separated from the next by a line containing only `---` (horizontal rule). Recommended shape (UI #240 should follow this; tolerate extra blank lines):

```markdown
---

**Submitted:** 2026-09-18T12:00:00Z
**Surface:** Pantry

Pantry tab feels slow when expanding aisles.
```

| Field | Required | Meaning |
| --- | --- | --- |
| **Submitted** | yes | ISO-8601 timestamp line (`**Submitted:** …`) |
| Body | yes | Free-text note (one or more paragraphs after a blank line following metadata) |
| **Surface** | no | `**Surface:** …` — tab or section |
| **Context** | no | `**Context:** …` — extra hint (route, widget, etc.) |

**Entry identity** for matching when archiving: **`Submitted` timestamp + body text** (strip whitespace on body; both must match).

If the backlog file is **missing** or has **no entries**, say so and stop after suggesting: run `just grocery-ui` and submit feedback once #240 is shipped, or paste 2–3 sample blocks into the file manually for testing.

**Read entries** (from repo root):

```bash
BACKLOG=".local/grocery_wizard/feedback_backlog.md"
test -f "$BACKLOG" || echo "missing"
python3 <<'PY'
import re
from pathlib import Path

path = Path(".local/grocery_wizard/feedback_backlog.md")
if not path.is_file():
    raise SystemExit(0)
raw = path.read_text(encoding="utf-8")
for chunk in re.split(r"\n---\n", raw):
    chunk = chunk.strip()
    if not chunk:
        continue
    m = re.search(r"\*\*Submitted:\*\*\s*(.+)", chunk)
    ts = m.group(1).strip() if m else "?"
    body = re.sub(r"^\*\*(Submitted|Surface|Context):\*\*.*\n?", "", chunk, flags=re.M).strip()
    print(f"[{ts}] {body[:80]}{'…' if len(body) > 80 else ''}")
PY
```

## Planning rules (same as `/create-issues`)

Follow **`.cursor/commands/create-issues.md`** — **Planning rules** section:

1. **Kind:** **bug** if broken/incorrect behavior, crashes, or regressions; else **enhancement** backlog.
2. **Area** (`gw-area-*`): **ui**, **parser**, **shopping**, **recipes**, **cli**, **other** — see area table in `.cursor/commands/work-on-issue.md`.
3. **Grouping:** Merge notes that share **kind + area** and can ship in one PR. Split when area differs or bug vs feature differs.
4. Use **Surface** / **Context** lines from the backlog when inferring area.
5. **Duplicates:** Before proposing a new issue, search open issues (`gh issue list` / `gh search issues`) when the note looks like an existing report; call out likely duplicates in the plan.

Valid areas match the table in `.cursor/commands/work-on-issue.md`.

## Your task

**Strict order** — do not skip approval before `gh issue create`.

### 1. Scan

Read **all** unprocessed entry blocks from `.local/grocery_wizard/feedback_backlog.md` (split on `\n---\n`). Report if any block lacks **Submitted** or body text.

### 2. Propose (chat only — no GitHub yet)

Post a **draft issue plan** that includes for each proposed GitHub issue (or merged group):

- Proposed **title**
- **Kind** (bug vs enhancement)
- **`gw-area-*`** label(s)
- **Source backlog entries** (Submitted time + short text quote)
- **Merge/split rationale** if multiple backlog lines map to one issue
- Whether you recommend **`bug`** and/or **`audit`** labels

Ask the user to **edit or approve** the list (add/remove/merge/split/reword). **Clarifying questions** are fine anytime before create.

**Do not** call `gh issue create` until the user confirms (e.g. “create them”, “LGTM”, or an edited plan they accept).

### 3. Create (after approval)

Create issues with **`gh`** using the same templates and labels as **`/create-issues`**:

- Enhancements: `grocery-wizard` + `gw-area-<area>`; body sections **Description**, **Expected behavior & manual test hints**, **Area**.
- Bugs: `--label bug` (+ area label when clear); mirror **`bug_report.yml`** sections.

Reference originating backlog text in the issue body (quoted or summarized).

Reply with issue numbers, URLs, and kind. Note **`/work-on-issue <n>`** for backlog items.

### 4. Archive processed backlog entries

After **successful** creation for approved items:

1. For each backlog entry that was filed (per **Submitted + body**), append the **same block** to **`.local/grocery_wizard/feedback_backlog.archived.md`**, then add a line **`GitHub issues:** #123, #456` (or whatever was created).
2. Rewrite **`.local/grocery_wizard/feedback_backlog.md`** to contain **only** entries **not** filed in this run (preserve order; keep leading `---` convention between blocks).
3. Tell the user how many entries were archived and how many remain in the active backlog.

If creation partially fails, archive **only** entries whose issues were created; leave the rest in the active file.

Example archive helper (set `filed` to `(submitted_iso, body_text)` keys and `issue_nums` before running):

```bash
python3 <<'PY'
import re
from pathlib import Path

backlog = Path(".local/grocery_wizard/feedback_backlog.md")
archive = Path(".local/grocery_wizard/feedback_backlog.archived.md")
filed: set[tuple[str, str]] = set()  # (submitted, body)
issue_nums: dict[tuple[str, str], list[int]] = {}


def parse_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return list of (submitted, body, original_block_with_leading_hr)."""
    blocks = []
    for chunk in re.split(r"\n---\n", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.search(r"\*\*Submitted:\*\*\s*(.+)", chunk)
        ts = m.group(1).strip() if m else ""
        body = re.sub(
            r"^\*\*(Submitted|Surface|Context):\*\*.*\n?", "", chunk, flags=re.M
        ).strip()
        blocks.append((ts, body, chunk))
    return blocks


def block_text(chunk: str) -> str:
    return f"\n---\n\n{chunk.strip()}\n"


if not backlog.is_file():
    raise SystemExit(0)
raw = backlog.read_text(encoding="utf-8")
parsed = parse_blocks(raw)
archive.parent.mkdir(parents=True, exist_ok=True)
remaining_chunks: list[str] = []
for ts, body, chunk in parsed:
    key = (ts, body)
    if key in filed:
        extra = issue_nums.get(key, [])
        nums = ", ".join(f"#{n}" for n in extra)
        archive.write_text(
            archive.read_text(encoding="utf-8") if archive.is_file() else "",
            encoding="utf-8",
        )
        with archive.open("a", encoding="utf-8") as f:
            f.write(block_text(chunk))
            if nums:
                f.write(f"\n**GitHub issues:** {nums}\n")
    else:
        remaining_chunks.append(chunk)
backlog.write_text(
    "".join(block_text(c) for c in remaining_chunks).lstrip("\n") or "",
    encoding="utf-8",
)
PY
```

(Fill `filed` and `issue_nums` in the script before running, or use equivalent logic in the agent turn.)

## Overrides

If auto-planning is wrong, adjust titles/bodies/labels before `gh issue create`, or edit issues on GitHub after creation.
