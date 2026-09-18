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

| Item | Value |
| --- | --- |
| **Path** | `.local/grocery_wizard/feedback_backlog.jsonl` (repo root; same tree as `DATA_DIR` in `src/grocery_wizard/config/__init__.py`) |
| **Archive** | `.local/grocery_wizard/feedback_backlog.archived.jsonl` (append-only; processed entries) |
| **Format** | **JSON Lines** — one JSON object per line, UTF-8, append-only |

Each entry object (fields from UI #240; tolerate missing optional keys):

| Field | Required | Meaning |
| --- | --- | --- |
| `ts` | yes | ISO-8601 timestamp when the note was submitted |
| `text` | yes | User free-text note |
| `surface` | no | Where in the app (e.g. tab name, page section) |
| `context` | no | Extra hint (route, widget id, session note) |

**Entry identity** for matching when archiving: pair **`ts` + `text`** (both must match).

If the backlog file is **missing** or **empty**, say so and stop after suggesting: run `just grocery-ui`, submit feedback via **Send feedback**, or seed 2–3 JSONL lines manually for testing.

**Read entries** (from repo root):

```bash
BACKLOG=".local/grocery_wizard/feedback_backlog.jsonl"
test -f "$BACKLOG" && wc -l "$BACKLOG" || echo "missing"
# Pretty-print for your own triage (skip blank lines):
while IFS= read -r line; do
  [ -n "$line" ] && echo "$line" | python3 -m json.tool
done < "$BACKLOG" 2>/dev/null || true
```

## Planning rules (same as `/create-issues`)

Follow **`.cursor/commands/create-issues.md`** — **Planning rules** section:

1. **Kind:** **bug** if broken/incorrect behavior, crashes, or regressions; else **enhancement** backlog.
2. **Area** (`gw-area-*`): **ui**, **parser**, **shopping**, **recipes**, **cli**, **other** — see area table in `.cursor/commands/work-on-issue.md`.
3. **Grouping:** Merge notes that share **kind + area** and can ship in one PR. Split when area differs or bug vs feature differs.
4. Use **`surface` / `context`** from the backlog when inferring area.
5. **Duplicates:** Before proposing a new issue, search open issues (`gh issue list` / `gh search issues`) when the note looks like an existing report; call out likely duplicates in the plan.

Valid areas match the table in `.cursor/commands/work-on-issue.md`.

## Your task

**Strict order** — do not skip approval before `gh issue create`.

### 1. Scan

Read **all** unprocessed lines from `.local/grocery_wizard/feedback_backlog.jsonl`. Ignore blank lines and invalid JSON (report count of skipped lines).

### 2. Propose (chat only — no GitHub yet)

Post a **draft issue plan** that includes for each proposed GitHub issue (or merged group):

- Proposed **title**
- **Kind** (bug vs enhancement)
- **`gw-area-*`** label(s)
- **Source backlog entries** (`ts` + short text quote)
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

1. For each backlog entry that was filed (per **`ts` + `text`**), append one line to **`.local/grocery_wizard/feedback_backlog.archived.jsonl`** — the original JSON object plus `"github_issues": [<numbers>]` (array of ints).
2. Rewrite **`.local/grocery_wizard/feedback_backlog.jsonl`** to contain **only** entries **not** filed in this run (preserve order of remaining lines).
3. Tell the user how many lines were archived and how many remain in the active backlog.

If creation partially fails, archive **only** entries whose issues were created; leave the rest in the active file.

Example archive helper (adjust `FILED_TS` / mapping to your approved set):

```bash
python3 <<'PY'
import json
from pathlib import Path

backlog = Path(".local/grocery_wizard/feedback_backlog.jsonl")
archive = Path(".local/grocery_wizard/feedback_backlog.archived.jsonl")
# filed: list of (ts, text) tuples that were turned into GitHub issues
filed: set[tuple[str, str]] = set()
issue_nums: dict[tuple[str, str], list[int]] = {}

def load_lines(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out

entries = load_lines(backlog)
archive.parent.mkdir(parents=True, exist_ok=True)
remaining = []
for obj in entries:
    key = (obj.get("ts", ""), obj.get("text", ""))
    if key in filed:
        obj = {**obj, "github_issues": issue_nums.get(key, [])}
        with archive.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    else:
        remaining.append(obj)
backlog.write_text(
    "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in remaining),
    encoding="utf-8",
)
PY
```

(Fill `filed` and `issue_nums` in the script before running, or equivalent logic in the agent turn.)

## Overrides

If auto-planning is wrong, adjust titles/bodies/labels before `gh issue create`, or edit issues on GitHub after creation.
