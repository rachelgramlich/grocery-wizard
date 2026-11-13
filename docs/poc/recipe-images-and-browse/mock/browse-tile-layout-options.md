# Browse tile layout — design mock

Fixes for **too-tall tiles** and **one image per row on phone**.

## Open the mock

- **Interactive HTML** (mobile + desktop): [`browse-tile-layout-options.html`](browse-tile-layout-options.html)  
  Open in a browser from this folder (double-click or drag into Chrome).

## Static previews (in this folder)

| View | File |
|------|------|
| Mobile options | `browse-tile-layout-options-mobile.png` |
| Desktop section | `browse-tile-layout-options-desktop.jpg` |
| Full scroll | `browse-tile-layout-options-full.jpg` |

**Option A (recommended):** 2 columns on phone + `object-fit: cover` + square tiles; desktop keeps `repeat(auto-fill, minmax(140px, 1fr))`.

CSS lives in `src/grocery_wizard/ui/static/app_theme.css` (`.gw-browse-grid`, `.gw-browse-tile-media`).
