# Browse recipes UI (for #491 / #492)

## Not this

The [**image fetch POC HTML report**](../scripts/image_fetch_poc.py) (`out/report.html`) is an engineering smoke test. It is **not** the product layout.

## Page shell

- Tab: **Browse recipes** (`browse` slug).
- Standalone page (no weekly rail); theme tokens from `app_theme.css`.

## Filters (`browse.filters`)

- Same widgets as meal planning (`render_meal_plan_filters`); **on the page** with **Apply** and **Reset**.
- **`browse.filters.has_image`:** checked = only rows with Notion **Files** populated; unchecked = include placeholders. **Default: checked** on first session visit.
- Defaults: Dinner + Weeknight Friendly + **Has image**.
- **Reset** clears all filters (including has image).
- Caption: `Showing N of M recipes`.

## Grid (`browse.grid`)

- Square tiles: **1:1**, **`object-fit: cover`** (avoid squashed previews).
- Subtitle: recipe name, centered, ~2 lines max.
- Placeholder: `#f3d4e6`, “No photo” when Files empty and filter allows.
- CSS grid: `repeat(auto-fill, minmax(140px, 1fr))`.
- Images: **Notion Files URLs only** (#490).

## Pagination

- `browse.load_more` — +24 per click; sort per #491 issue body.

## Interaction

- **V1 (#491):** no card tap; `pointer-events: none` / no misleading hover (#492).
- **V2 (#492):** tap adds/pins to this week’s meal plan.

## Reference mock

- [`mock/browse-recipes-ui-mock.html`](../mock/browse-recipes-ui-mock.html)
