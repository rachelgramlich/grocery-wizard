# Repository layout

Grocery Wizard is a **Python package** (`src/grocery_wizard/`) plus **docs**, **tests**, and **agent tooling**. The product surface is **Streamlit**; data lives in **Notion**.

## Top level

```
grocery-wizard/
├── src/grocery_wizard/      # installable package (all product code)
├── tests/                   # pytest (mirrors src layout + fixtures)
├── docs/                    # human docs (see docs/README.md)
├── scripts/                 # one-off maintainer scripts (see scripts/README.md)
├── .cursor/                 # slash commands, skills, rg-ai submodule
├── .github/                 # CI workflows, issue templates
├── .streamlit/              # Streamlit theme and server config
├── AGENTS.md                # agent + backlog conventions
├── CONTRIBUTING.md          # lint, types, review standards
├── Justfile                 # just recipes (setup, check, grocery-ui, …)
├── pyproject.toml           # deps, ruff, pytest paths
└── README.md                # repo front door
```

**Gitignored runtime data:** `.env` / `secrets.toml`, `.local/grocery-wizard/`, `.venv/`.

## Package (`src/grocery_wizard/`)

Folders are grouped by **job**, not by layer. Dependency flow is mostly: `ui` → domain modules → `integrations` / `config`.

| Folder | Responsibility |
| --- | --- |
| `ui/` | Streamlit entry (`app.py`), page bodies (`views/`), stable IDs (`ids.py`), Notion cache |
| `config/` | Environment loading, `store_aisles.txt`, committed defaults |
| `integrations/` | Notion API, NYT Cooking, household auth helpers |
| `recipes/` | URL scrape, metadata classify, add recipe to Notion |
| `ingredients/` | Parse, normalize, sync ingredient lines (see `ARCHITECTURE.md`) |
| `planning/` | Weekly meal suggestion and filters |
| `shopping/` | Grocery list build, pantry match/exclude |
| `cli/` | Deprecated CLI shims (Streamlit is the product) |
| `lib/` | Small shared helpers (e.g. prompts) |
| `dev/` | Performance audit harness and other dev-only tooling |

```
src/grocery_wizard/
├── ui/
│   ├── app.py                 # thin entry: nav, theme, cache controls
│   ├── ids.py                 # page.block.control IDs
│   ├── views/                 # one module per primary page
│   │   └── weekly_plan/       # multi-step weekly + grocery flow
│   └── static/                # CSS assets
├── integrations/
├── recipes/
├── ingredients/
├── planning/
├── shopping/
├── config/
├── cli/
├── lib/
└── dev/
    └── perf_audit/            # `just performance-audit`
```

## Tests (`tests/`)

```
tests/
├── src/grocery_wizard/        # mirrors package folders (test_*.py)
└── fixtures/
    └── golden_grocery_weeks/  # exported list regressions (`just golden-grocery`)
```

UI tests import paths from `tests/src/grocery_wizard/ui/ui_source.py` — do not hard-code `app.py` paths in individual tests.

## Documentation (`docs/`)

| Subfolder | Topics |
| --- | --- |
| `architecture/` | This file, repo split history |
| `operations/` | Cloud deploy, Notion CI, remote access |
| `ui/` | UI map, weekly flow, perf research |
| `quality/` | Golden grocery weeks, performance audit |
| `issues/` | Draft GitHub issue write-ups |
| `poc/` | Experiments (not shipped code) |

Index: [`docs/README.md`](../README.md).

## Agent and CI tooling

| Path | Role |
| --- | --- |
| `.cursor/commands/grocery-wizard/` | App-specific slash commands |
| `.cursor/commands/shared/` → `rg-ai` | Shared commands (work-on-issue, tidy-project, …) |
| `.cursor/skills/tidy-first/` | Inline structure-only tidying while coding |
| `.github/workflows/` | `just ci`, optional live Notion read-only job |

## Where to add new files

| Kind of change | Put it here |
| --- | --- |
| New Streamlit page or widget | `src/grocery_wizard/ui/views/` (+ IDs in `ids.py`, doc in `docs/ui/ui-map.md`) |
| New Notion or NYT integration | `src/grocery_wizard/integrations/` |
| New domain logic (no UI) | Matching folder under `recipes/`, `shopping/`, etc. |
| Regression test | Mirror path under `tests/src/grocery_wizard/` |
| Operator runbook | `docs/operations/` |
| UI or UX spec | `docs/ui/` or `docs/issues/` until shipped |
| Spike / prototype | `docs/poc/<name>/` until promoted into `src/` |
