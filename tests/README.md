# Tests

Pytest tree under `tests/src/grocery_wizard/` mirrors the installable package. Fixtures live in `tests/fixtures/` (golden grocery weeks, Notion JSON snapshots, etc.).

## Path and source helpers

Do not hard-code `src/grocery_wizard/...` paths in individual tests.

| Helper | Import from | Use for |
| --- | --- | --- |
| `REPO_ROOT`, `SRC_PACKAGE_ROOT`, `package_module_source` | `tests/repo_paths.py` | Any package module on disk |
| `APP_PATH`, `app_source`, `weekly_plan_source`, … | `tests/src/grocery_wizard/ui/ui_source.py` | Streamlit UI source strings |
| `apptest_from_app`, `apptest_start_app` | `ui_source` | Headless Streamlit AppTest |

Canonical anchors are defined in `src/grocery_wizard/paths.py` — see [`docs/architecture/path-anchors.md`](../docs/architecture/path-anchors.md).

## Commands

```bash
just check          # ruff + format check + full pytest
just smoke-ui       # holistic UI AppTest subset
just golden-grocery # grocery list golden weeks
```

Holistic UI smoke is marked with `@pytest.mark.holistic_ui_smoke` in `test_holistic_ui_smoke_apptest.py`.