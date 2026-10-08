# Weekly tab UX spec (Create weekly plan)

Design for [#325](https://github.com/rachelgramlich/grocery-wizard/issues/325) and follow-up implementation issues. **Source of truth** for rail behavior, collapse rules, happy path, and copy goals on the `weekly` page.

Related: closed [#209](https://github.com/rachelgramlich/grocery-wizard/issues/209) (labels, dev tools, partial collapse of meal builder). Block IDs remain in [`ui-map.md`](ui-map.md); this doc describes **user-facing** behavior.

## Goals

1. **One obvious next action** at each moment (one primary button per stage).
2. **Finished stages feel done** — muted collapsed summaries, not full duplicate UI.
3. **Current stage is obvious** — rail highlight + scroll into view after primary actions.
4. **Less visual noise** — no numbered steps (`1.`, `1a`, `Steps:`) in the UI; shorter copy (final copy pass).
5. **One scrollable page** — same Streamlit page; change how blocks look and collapse.

## Step rail (3 steps, not 4)

The rail is **navigation and progress**, not a separate wizard. **Copy & finish** is part of **Grocery list**, not its own rail step.

| Rail step | User-facing label (draft) | Maps to blocks (`ui-map.md`) |
|-----------|---------------------------|------------------------------|
| **1** | **Get started** | `weekly.plan_start` |
| **2** | **Plan meals** | `weekly.meals`, `weekly.meals.build`, `weekly.meals.list`, `weekly.meals.save` |
| **3** | **Grocery list** | `weekly.grocery_pre_build`, `weekly.grocery_recipe_review`, `weekly.grocery_result` (+ summary / customize) |

### Grocery list sub-stages (single rail step)

Within step **3**, the happy path is sequential but **one rail pill stays active** until the list is built:

1. **Pre-build** — pantry/recurring/extras (mostly collapsed expanders) → **Create grocery list**
2. **Review ingredients** — per-recipe editors → **Build final list** (main flow; required for all users)
3. **Result** — summary (collapsed by default), customize, copy buttons

Do not add a fourth rail step for copy/finish. Optionally show a **sub-caption** under the rail during step 3 (e.g. “Review ingredients” vs “Your list”) without a new step number.

## Rail state: active / done / upcoming

- **Active:** accent border on the open block + filled rail segment.
- **Done:** check + grey rail segment; block collapsed to a **summary row** when rules below say so.
- **Upcoming:** dimmed rail segment; body hidden or minimal placeholder.

**Click a rail step** to expand that stage again and scroll it into view (`weekly_expanded_step` in session state).

## When each rail step is “done”

| Step | Done when |
|------|-----------|
| **Get started** | User clicked **Continue** (show compact “Started: … · Change”) |
| **Plan meals** | `_matching_saved_plan(recipe_names)` — plan in Notion matches current meals |
| **Grocery list** | `grocery_result` in session state (final list shown) |

**Auto-save before grocery** (`_ensure_weekly_plan_saved_before_grocery`) counts as a Notion save for step 2 done/collapse — user should not need a separate **Save plan to Notion** click to get collapse, though the explicit save button remains for “save without building a list.”

## Plan meals: collapse and saved-plan entry

### New weekly plan

- After **Build my plan:** step 2 **active**; **Your meals** expanded (swaps are common).
- **Meal builder** collapsed once a plan exists (today’s expander pattern); force-open via **Edit meal builder** or rail click.
- Step 2 → **done** only after Notion save fingerprint matches (manual save or auto-save on grocery).

### Continue from saved plan

- Land **post-build, pre-save-for-this-session:** meals loaded, **Your meals** expanded, **meal builder** collapsed.
- Step 2 **active** (not done) — user may swap before saving again.
- Do not treat “loaded from Notion” alone as done until fingerprint matches after edits.

## Primary actions and scroll

Scroll into view **only** after these primary buttons (set `weekly_scroll_target`, clear after one run):

- **Continue** (get started)
- **Build my plan**
- **Create grocery list**
- **Build final list** (per-recipe review)

Optional: skip scroll on **Save plan to Notion** unless UX testing shows it helps.

## Dev vs main flow

| Feature | Placement |
|---------|-----------|
| **Per-recipe ingredient review** | **Main flow** — after **Create grocery list**, before final list |
| **Dev tools** (jump buttons) | `weekly_plan_mode == "dev"` only — existing expander; label **`Dev: …`** |
| **Item sources** on final list | Prefer **`Dev: item sources`** or default collapsed expander |
| Session **Dev mode** on start screen | Unchanged semantics (no Notion save); naming cleanup in copy pass |

Power-user paths use the **`Dev:`** prefix so they do not look like required happy-path steps. **Review ingredients is not Dev** — it stays the normal path.

## Visual noise to remove (implementation + copy pass)

- Remove top line `Steps: 1. Meals → 2. Grocery list` and headings `### 1. Meals`, `#### 1a.`, `#### 1b.`.
- Replace expander titles like `1a. Build your meal list` with plain names (**Build meals**, **Your meals**).
- Keep block IDs in code/tests/docs (`weekly.meals.build`, etc.).

## Friction: keep vs cut

| Keep | Reason |
|------|--------|
| **Build my plan** | Clear “fill slots” action for new plans |
| **Create grocery list** → review → **Build final list** | Main path including review |
| **Save plan to Notion** | Save without grocery |
| Overwrite / week-target confirms | Safety |

| De-emphasize or collapse | Reason |
|--------------------------|--------|
| Meal builder after plan exists | Focus on **Your meals** |
| Plan meals block after Notion save | Summary until user expands |
| Pre-build expanders | Defaults are enough for most users |
| Summary (build result) | Collapsed by default |

| Later (optional follow-ups) | |
|-----------------------------|---|
| Auto-**Continue** when saved plan row selected | Fewer clicks on start |
| Hide session Dev mode behind env flag | #209 intent |

## Code touchpoints (implementation)

| Concern | Files |
|---------|--------|
| Page orchestration | `src/grocery_wizard/ui/pages/weekly_plan/flow.py` |
| Start + meals | `src/grocery_wizard/ui/pages/weekly_plan/plan_entry.py` |
| Grocery + result | `src/grocery_wizard/ui/pages/weekly_plan/grocery_list_ui.py` |
| Per-recipe review | `src/grocery_wizard/ui/pages/weekly_plan/recipe_review.py` |
| Save / fingerprint | `src/grocery_wizard/ui/pages/weekly_plan/state.py` |
| Rail / step UI (new) | e.g. `src/grocery_wizard/ui/pages/weekly_plan/step_ui.py` |
| Dim / scroll CSS | `src/grocery_wizard/ui/static/app_theme.css` |

## Implementation split (GitHub)

Spec delivered in #325; implementation:

| Order | Issue | Scope |
|-------|-------|--------|
| 1 | [#328](https://github.com/rachelgramlich/grocery-wizard/issues/328) | Step rail, block states, CSS |
| 2 | [#329](https://github.com/rachelgramlich/grocery-wizard/issues/329) | Saved-plan entry, Notion save collapse |
| 3 | [#330](https://github.com/rachelgramlich/grocery-wizard/issues/330) | Grocery stage layout, scroll, rail expand (main-path review) |
| 4 | [#331](https://github.com/rachelgramlich/grocery-wizard/issues/331) | Copy pass (last) |

Suggested PR order matches the table. Use `tidy-first` (**S** vs **B**) within each issue.

Each PR: `just check`, UI smoke when Notion preflight passes, **`Browser smoke:`** line in PR.

## Manual test (full happy path)

**Surface:** Streamlit → **Create weekly plan**.

1. **New plan:** start → meal count → **Build my plan** → swap a meal → **Save plan to Notion** (or **Create grocery list** and confirm auto-save) → step 2 collapses when saved.
2. **Grocery:** **Create grocery list** → per-recipe review → **Build final list** → copy list; step 3 done on rail.
3. **Saved plan:** continue saved plan → lands on **Your meals**, builder collapsed; swap → save → grocery as above.
4. Rail: click done step to re-expand; completed blocks look muted.

**Expected:** One obvious primary action; no numbered step chrome; review is normal, not hidden in Dev.
