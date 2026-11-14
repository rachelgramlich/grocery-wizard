# Documentation map

Start here when you need a guide, UI reference, or quality sign-off doc. **Code** lives under `src/grocery_wizard/`; **this tree** is for humans and agents.

| Folder | What belongs here |
| --- | --- |
| [`architecture/`](architecture/repo-layout.md) | Repo layout, history notes (not package internals) |
| [`operations/`](operations/household-deploy.md) | Deploy, auth, Notion CI secrets, phone / remote access |
| [`ui/`](ui/ui-map.md) | Streamlit pages, block IDs, weekly flow, UI perf research |
| [`quality/`](quality/grocery-quality.md) | Grocery list golden weeks, performance reports and harness |
| [`issues/`](issues/README.md) | Draft issue specs (not committed product code) |
| [`poc/`](poc/recipe-images-and-browse/README.md) | Spikes and mocks — not production |

## Quick links

| I want to… | Read |
| --- | --- |
| Use the app day to day | [`src/grocery_wizard/README.md`](../src/grocery_wizard/README.md) |
| Wire Notion databases | [`src/grocery_wizard/config/README.md`](../src/grocery_wizard/config/README.md) |
| Understand the whole repo tree | [`architecture/repo-layout.md`](architecture/repo-layout.md) |
| Ship to Streamlit Cloud | [`operations/household-deploy.md`](operations/household-deploy.md) |
| Name a UI control in an issue | [`ui/ui-map.md`](ui/ui-map.md) |
| Sign off grocery list output | [`quality/grocery-quality.md`](quality/grocery-quality.md) |
| Run `/performance-audit` | [`quality/performance-audit.md`](quality/performance-audit.md) |
| Contribute / lint / tests | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Agent workflows | [`AGENTS.md`](../AGENTS.md) |

## Package-local docs

Some design notes stay next to the code they describe:

- [`src/grocery_wizard/ingredients/ARCHITECTURE.md`](../src/grocery_wizard/ingredients/ARCHITECTURE.md) — ingredient storage vs grocery-list pipelines

Do not add new markdown under `src/grocery_wizard/docs/`; use the folders above.
