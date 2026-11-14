# Browse recipes (enhancement draft)

> **Filed:** https://github.com/rachelgramlich/grocery-wizard/issues/491 — use `/work-on-issue 491`.
> **Labels:** `grocery-wizard`, `gw-area-ui`
> **Depends on:** Notion **Files** image column on recipes (see `recipe-image-backfill.md` for populating it).

## Description

Add a new top-level Streamlit page so users can visually browse the recipe library before or outside the weekly plan builder.

- **Page slug:** `browse`
- **User-facing tab label:** **Browse recipes**
- **Layout:** Responsive, Instagram-like **square** grid; recipe **name** as subtitle; **`object-fit: cover`** (no squashed tiles).
- **Filters:** Same filter set as meal planning (`render_meal_plan_filters` / `MealPlanFilters` / Notion schema filter + checkbox columns + ingredient include/exclude). Filters are **on the page** (not in a popover or dropdown-only pattern). Include an **Apply** button; changing widgets does not refresh the grid until Apply.
- **Has image (browse-only):** Checkbox — **checked** = only recipes the grid can show a photo for (displayable URL); **unchecked** = also include placeholder tiles and Notion-only attachments. **Default checked** on first session visit.
- **Defaults (first visit in a session):** `Meal = Dinner`, `Dinner: Weeknight Friendly = true`, and **Has image checked** (same meal defaults as `default_filters()` plus this browse filter).
- **Reset:** Clears **all** filters including defaults (empty filter state — not the dinner/weeknight defaults).
- **Session persistence:** Draft filter widget state and last-**applied** filter state live in `st.session_state` for the current session only (no cross-session persistence).
- **Sort order (after Apply):**
  1. `Selection count` ascending (missing/non-numeric → 0)
  2. `Rejection count` ascending (missing/non-numeric → 0)
  3. Notion `last_edited_time` ascending (oldest first)
  4. Within ties, **random** order (seeded per Apply so grid is stable until next Apply)
- **Pagination:** Load-more pattern; **24** recipes per page by default.
- **Missing images:** Placeholder tiles only when **Has image** is **unchecked** and Apply includes rows with an empty Files column.
- **Images:** Read from a Notion **Files** property on the recipe database (configurable column name; document in `docs/ui/ui-map.md`). Do not hotlink external URLs in the grid — display Notion-hosted file URLs from that column.
- **V1 interaction:** Cards are **not** clickable (no navigation, no plan actions).
- **V2 (out of scope for V1):** Tap/click adds recipe to **this week’s plan** — file a follow-up or section in this issue only as future work.

**Engineering hygiene (per `AGENTS.md`):**

- Register `PAGE_SLUG_BROWSE` (or equivalent) and page label in `src/grocery_wizard/ui/ids.py` and `src/grocery_wizard/ui/views/__init__.py`.
- Update `docs/ui/ui-map.md` with page, blocks (e.g. `browse.filters`, `browse.apply`, `browse.grid`, `browse.load_more`), and control IDs.
- Extend holistic UI smoke (`just smoke-ui`) to import/render the browse page.
- Add perf-audit scenario in `src/grocery_wizard/dev/perf_audit/scenarios.py` covering Apply + load more.
- Browser smoke optional when Notion CI preflight succeeds.

**Notion / data model:**

- Extend recipe list loading so the Files image column is included in `filter_properties` / `Recipe` (URL(s) for display).
- `last_edited_time` must be available for sort (page metadata from query or stored on `Recipe`).

## Expected behavior & manual test hints

**Surface:** Streamlit → page picker → **Browse recipes**

**Steps:**

1. Open **Browse recipes**. Confirm default applied filters match **Dinner** + **Weeknight Friendly** and the grid reflects them after first load (initial Apply or auto-apply on first render — pick one behavior and document it; prefer explicit first Apply only if defaults are pre-filled but grid waits for Apply).
2. Change filters without Apply — grid unchanged.
3. Click **Apply** — grid updates to matching recipes only; sort order matches spec (spot-check a recipe with low selection count vs high).
4. Click **Reset** — all filters cleared; grid shows unfiltered library (or clarify empty-filter semantics in code comments).
5. Navigate away and back within the same session — last applied filters and draft widgets restore from `session_state`.
6. New browser session — defaults return to Dinner + weeknight.
7. Scroll/load more — next 24 recipes append; performance acceptable on full library.
8. Recipe with no Files image — placeholder visible, name subtitle present.
9. Run `just smoke-ui` — passes including browse page.

**V1 negative:** Clicking a card does nothing.

## Area

ui

## Acceptance criteria

- [ ] New top-level tab **Browse recipes** (`browse` slug) in page picker.
- [ ] Filter row matches meal-plan filter capabilities; **Apply** and **Reset** buttons on page.
- [ ] Default filters: Dinner + Dinner: Weeknight Friendly on first session visit.
- [ ] Reset removes all filters including defaults.
- [ ] Filter draft + last-applied state in `st.session_state` only.
- [ ] Sort: selection count ↑, rejection count ↑, last_edited_time ↑, random tie-break.
- [ ] Load-more pagination, page size 24.
- [ ] Grid uses Notion Files column images; placeholder when missing.
- [ ] Responsive multi-column grid with name subtitles.
- [ ] No card tap behavior in V1.
- [ ] Square tiles + `object-fit: cover` (no stretched images).
- [ ] `ids.py`, `ui-map.md`, smoke + perf-audit updated.

## Future work (V2)

- #492 — Card click adds recipe to current weekly plan.
