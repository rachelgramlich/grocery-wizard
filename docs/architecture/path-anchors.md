# Path anchors

Filesystem paths are owned in two places so production code, tests, and docs do not diverge.

## Production (`src/grocery_wizard/paths.py`)

| Name | Points to |
| --- | --- |
| `PACKAGE_ROOT` | `src/grocery_wizard/` |
| `REPO_ROOT` | Repository root (parent of `src/`) |
| `UI_APP_PATH` | Streamlit entry (`ui/app.py`) |
| `GOLDEN_GROCERY_WEEKS_DIR` | `tests/fixtures/golden_grocery_weeks/` |
| `BUNDLED_NLTK_DATA_DIR` | `resources/nltk_data/` |

Use these instead of `Path(__file__).parents[N]` in new code.

**Streamlit bootstrap:** `ui/app.py` still computes a one-time repo root before `sys.path` is set, then imports `REPO_ROOT` from `paths` for `PYTHONPATH` hot-reload parity with tests.

## Tests (`tests/repo_paths.py`)

| Name | Role |
| --- | --- |
| `REPO_ROOT`, `SRC_PACKAGE_ROOT` | Re-exported from `paths` (package + repo) |
| `UI_SRC_ROOT`, `UI_TEST_HELPERS` | UI tree under `tests/src/grocery_wizard/ui/` |
| `FIXTURES_DIR` | Shared pytest fixtures |
| `package_module_source(rel)` | Read any file under `src/grocery_wizard/` as UTF-8 text |

UI string-regression tests should use helpers in `tests/src/grocery_wizard/ui/ui_source.py` (`app_source`, `weekly_plan_source`, `apptest_from_app`, …) rather than path literals.

## Related constants (not in `paths.py`)

| Constant | Owner |
| --- | --- |
| `APP_THEME_STATIC_CSS` / `UI_STATIC_DIR` | `ui/theme.py` |
| `DEFAULT_EMPTY_PANTRY_LINES` | `shopping/pantry.py` |
| `BROWSE_EMPTY_FILTER_HTML` | `ui/browse_logic.py` |
| `NAME_LINK_STALE_VERIFY_MESSAGE` | `shopping/grocery_list.py` |
| HTTP `USER_AGENT` / `REQUEST_TIMEOUT` | `recipes/scraper.py` (shared by NYT client) |
| `NOTION_BOUNDARY_ERRORS` | `integrations/notion_io_errors.py` (allowed `except` tuple at API boundaries) |

See also: [`repo-layout.md`](repo-layout.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md).