# Grocery Wizard

Personal recipe and meal-planning tool backed by **Notion**: save recipes from the web, plan dinners, and build a grocery list sorted by store aisle.

## What this repo is for

- **Recipes** — scrape ingredients from URLs (or sync from NYT Cooking) into your Notion Recipes database.
- **Weekly planning** — pick dinners with variety filters (protein, cuisine, weeknight-friendly, etc.).
- **Shopping** — combine planned meals, exclude pantry staples, add recurring items, export a list in walk order.

Notion holds recipes, pantry, recurring items, and saved meal plans. A small local cache (`.local/grocery_wizard/`) supports session hints; see the package README for details.

## How to use it

**Primary workflow:** run the Streamlit app from the repo root (so `.streamlit/config.toml` loads):

```shell
just grocery-ui
# or: uv run streamlit run src/grocery_wizard/ui/app.py
```

Use the UI to create a weekly plan, review ingredients, and generate your grocery list.

**NYT recipe box:** use the Streamlit app (`just grocery-ui`) → expand **Sync from NYT Cooking** under the title bar.

Full command reference, NYT credentials, meal-planning defaults, aisle config, and Notion schema: **[`src/grocery_wizard/README.md`](src/grocery_wizard/README.md)**.

### Documentation

| Doc | Contents |
|-----|----------|
| [`src/grocery_wizard/README.md`](src/grocery_wizard/README.md) | Day-to-day usage (Streamlit), one-time Notion setup, project layout |
| [`src/grocery_wizard/config/README.md`](src/grocery_wizard/config/README.md) | Pantry / recurring / weekly-plan Notion databases |
| [`src/grocery_wizard/docs/remote-access.md`](src/grocery_wizard/docs/remote-access.md) | Phone access (local Wi‑Fi vs hosted) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Lint, tests, and code review standards |
| [`AGENTS.md`](AGENTS.md) | Cursor agents and GitHub backlog workflow |

---

## Developer setup

### One-time machine setup

1. Install [brew](https://brew.sh/): a package manager.
   - Install it directly as a package from its GitHub repo.
   - Follow installation steps, including command to setup your shell, by exporting path -> .zshrc.

2. Install other tools
   ```shell
   brew install \
     just
     uv
   ```

### Local setup

1. Copy `.env.example` to `.env` and configure Notion (and optional NYT) — steps in [`src/grocery_wizard/README.md` § One-time setup](src/grocery_wizard/README.md#one-time-setup).
2. Update the Python environment:
   ```shell
   just setup
   ```
3. Verify Notion wiring by opening **`just grocery-ui`** and confirming recipes load.

### Cursor (optional)

The enhancement backlog lives on **GitHub Issues** (label `grocery-wizard`). Agents should follow [AGENTS.md](AGENTS.md). Slash commands live in **`.cursor/commands/`** (committed). Requires `gh` for backlog commands. Do not commit `.cursor/mcp.json` (tokens).

`just setup` links Streamlit’s skill into `.cursor/skills/developing-with-streamlit` (from `.venv`). **`tidy-first`** (inline while coding) lives under `.cursor/skills/`. Whole-repo tidying is the slash **command** **`.cursor/commands/tidy-project.md`** → type **`/tidy-project`** in **Agent** chat at the repo root (same as `/work-on-issue`). See [AGENTS.md](AGENTS.md) if it does not appear.
