---
name: sync-store-aisles
description: Reconcile store_aisles.txt keywords against every normalized ingredient in the Notion recipe database.
---

# Sync store aisles from Notion

**Scope:** Pull **all** recipe ingredients from Notion, normalize to unique grocery item names (no amounts or prep), find names not covered by `src/grocery_wizard/config/store_aisles.txt`, add missing keywords on a branch, and open a PR when placement is clear or after the user confirms uncertain items.

**Area:** **shopping** + **parser** + **recipes** — see `.cursor/commands/work-on-issue.md` area → files table.

**Config file:** `src/grocery_wizard/config/store_aisles.txt` (format and walk order: `src/grocery_wizard/README.md` § Grocery list aisle order).

This is **config/data**, not app UI. **Browser smoke: N/A (non-UI)** unless you also changed Streamlit code.

---

## Your task

### 1. Preflight (Notion + repo)

```bash
git fetch origin main
test -n "${NOTION_API_KEY:-}" && PYTHONPATH=src uv run python -c "
from grocery_wizard.config import load_config
from grocery_wizard.integrations.notion import NotionRecipesDB
cfg = load_config()
db = NotionRecipesDB(cfg)
print('recipes:', len(db.query_recipes()))
"
```

- If preflight fails (missing secrets, Notion error), **stop** and tell the user what env is missing. Cloud agents: secrets are process env — missing `.env` is OK when vars are set.
- Requires **`gh`** authenticated when you open a PR.

### 2. Extract unique ingredients from Notion

Use the **same pipeline as the grocery list** so results match what shoppers see:

1. `NotionRecipesDB(load_config()).query_recipes()` — every recipe page.
2. For each recipe’s ingredients text:
   - `parse_ingredients_text` + `apply_removals` from `src/grocery_wizard/ingredients/sync.py` (same as `_ingredient_lines_from_stored_text` in `grocery_list.py`).
3. For each remaining line, canonical name via `normalize_ingredient` from `src/grocery_wizard/ingredients/normalize.py` (strips amounts and prep — e.g. `zest of 1/2 lemon` → `lemon`). Drop empty / junk lines.
4. **Deduplicate** on lowercase canonical name. Keep one representative spelling (prefer the normalized string from the pipeline).

You may run a one-off script under `uv run` with `PYTHONPATH=src`; do **not** commit throwaway scripts unless the user asks to productize this.

**Optional report** (paste in chat before editing the txt file):

- Total recipes scanned, total raw lines, unique canonical names count.
- Sample of 5–10 names that already classify correctly vs names that hit **`other`**.

### 3. Compare to `store_aisles.txt`

1. Load keywords: `load_store_aisles()` / `parse_store_aisles_file` from `src/grocery_wizard/shopping/store_aisles.py`.
2. For each unique canonical name, treat it as **covered** when `classify_aisle(name)` returns an aisle **other than** `other` (same matcher the app uses at checkout walk order).
3. **Missing** = unique names that classify as **`other`** but are real grocery nouns (not typos, not one-off “serve with …” prose). Cross-check: name not already present as a keyword line (case-insensitive) in any section.

Do **not** remove existing keywords in this workflow unless the user explicitly asks.

### 4. Branch

Off latest `main`:

```bash
git checkout main && git pull origin main
git checkout -b cursor/sync-store-aisles-84c7
```

(Use `cursor/<short-theme>-84c7` if this branch name is taken.)

### 5. Add missing keywords

Edit **`src/grocery_wizard/config/store_aisles.txt` only** (unless tests need a fixture update — rare).

**Placement rules:**

- Put each keyword under the **most likely** aisle section (`# --- aisle_id: Display label ---`).
- Follow file conventions: **one keyword per line**; **longer / more specific phrases before shorter ones** in the same section (see file header comment).
- Use lowercase keywords unless the file already uses a special form for that item.
- After edits, re-run classification on the missing set — every added name should no longer land in **`other`**.

**Uncertain placement:**

- Do **not** guess on specialty items (spirits, obscure sauces, dual-aisle goods, “for serving” garnishes, brand-specific products).
- For each uncertain name, either:
  - Add a **comment-only** line in the file: `# UNCERTAIN: <canonical name> — <short question>` **and** list the same questions in chat, **or**
  - Skip adding that keyword until the user answers.
- **Stop before commit/PR** if any `# UNCERTAIN` lines remain or open questions are unanswered. Ask the user to pick an aisle (or “skip / leave in Other”).

When the user confirms, replace `# UNCERTAIN` entries with the chosen keyword line in the right section and remove the comment.

### 6. Verify

```bash
just check
```

Extra sanity (fast):

```bash
PYTHONPATH=src uv run python -c "
from grocery_wizard.config import load_config
from grocery_wizard.integrations.notion import NotionRecipesDB
from grocery_wizard.ingredients.normalize import normalize_ingredient
from grocery_wizard.ingredients.sync import apply_removals, parse_ingredients_text
from grocery_wizard.shopping.store_aisles import classify_aisle, load_store_aisles

cfg = load_config()
names: set[str] = set()
for r in NotionRecipesDB(cfg).query_recipes():
    if not r.ingredients:
        continue
    lines, rem = parse_ingredients_text(r.ingredients)
    for line in apply_removals(lines, rem):
        n = normalize_ingredient(line)
        if n:
            names.add(n.lower())
other = sorted(n for n in names if classify_aisle(n) == 'other')
print('unique names:', len(names), 'still other:', len(other))
if other[:20]:
    print('sample other:', other[:20])
"
```

Investigate any surprising **`other`** leftovers; fix keywords or ask the user.

### 7. Commit and PR

- Commit message example: `chore(config): add store aisle keywords from Notion ingredient audit`
- PR title example: `chore(config): sync store aisle keywords from Notion recipes`
- PR body: repo **`.github/pull_request_template.md`**, **Manual verification** filled (what you ran, **`Browser smoke: N/A (non-UI)`**), list of added keywords by aisle, and note any items **skipped** or user-confirmed.
- Open **ready for review** (not draft) unless the user asks for draft.
- No GitHub issue is required; omit `Closes #N` unless the user tied this to an issue.

Post agent sign-off when checks pass:

```bash
gh pr comment <pr-url> --body "**Manual verification:** passed (/sync-store-aisles).

- \`just check\`
- Notion preflight + post-edit classify sanity script
- **Browser smoke: N/A (non-UI)**"
```

### 8. Report to the user

Summarize:

- Counts (recipes, unique ingredients, keywords added).
- Aisle breakdown of additions.
- Any names still in **`other`** by choice or pending user input.
- PR link when shipped.

---

## Collision check

This workflow is a **slash command only** — do **not** add `.cursor/skills/sync-store-aisles/`.
