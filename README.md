# Grocery Wizard

Plan dinners, manage pantry staples, and build aisle-sorted grocery lists from recipes stored in Notion.

Grocery Wizard is a Streamlit app for household meal planning: save recipes from the web (or NYT Cooking), pick a weekly menu with variety filters, subtract what is already in your pantry, and walk the store with a list grouped by aisle. Recipes, pantry, recurring items, and saved plans live in Notion; the app keeps secrets on the server when deployed.

**Hosted app:** [grocerywizard.streamlit.app](https://grocerywizard.streamlit.app) (Google sign-in for household members). **Local:** `just grocery-ui` from this repo.

> **Streamlit profile card:** set the display name under **Manage app → Settings → General → App name** (otherwise SCC may show **“Sign in – Google Accounts”** from the OAuth redirect). This README supplies the GitHub/social blurb; the **My apps** tile is mostly name + screenshot. Use `page_title="Grocery Wizard"` in the app entrypoint. After Secrets are valid, **Reboot app**; preview refresh can take hours.

## What this app does

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
| [`docs/household-deploy.md`](docs/household-deploy.md) | Streamlit Community Cloud deploy, auth, feedback inbox |
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

1. Copy `secrets.toml.example` to **`secrets.toml`** at repo root (or `.env` from `.env.example`) and configure Notion — see [`src/grocery_wizard/README.md` § One-time setup](src/grocery_wizard/README.md#one-time-setup) and [`docs/household-deploy.md`](docs/household-deploy.md).
2. Update the Python environment:
   ```shell
   just setup
   ```
3. Verify Notion wiring by opening **`just grocery-ui`** and confirming recipes load.

### Cursor (optional)

The enhancement backlog lives on **GitHub Issues** (label `grocery-wizard`). Agents should follow [AGENTS.md](AGENTS.md). Slash commands live in **`.cursor/commands/`** (committed). Use **`/create-command`** when adding a new command so it does not collide with a skill of the same name. Requires `gh` for backlog commands. Do not commit `.cursor/mcp.json` (tokens).

`just setup` links Streamlit’s skill into `.cursor/skills/developing-with-streamlit` (from `.venv`). **`tidy-first`** (inline while coding) lives under `.cursor/skills/`. Whole-repo tidying is the slash **command** **`.cursor/commands/tidy-project.md`** → type **`/tidy-project`** in **Agent** chat at the repo root (same as `/work-on-issue`). To reconcile **`store_aisles.txt`** with ingredients in Notion, use **`/sync-store-aisles`**. For hands-on UI review through grouped GitHub issues, use **`/app-review`**. See [AGENTS.md](AGENTS.md) if commands do not appear.
