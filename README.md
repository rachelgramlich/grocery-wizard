# One-Time Setup

1. Install [brew](https://brew.sh/): a package manager.
   - Install it directly as a package from its GitHub repo.
   - Follow installation steps, including command to setup your shell, by exporting path -> .zshrc.

2. Install other tools
   ```shell
   brew install \
     just
     uv
   ```

# Local setup

1. Update local environment by running:
   ```shell
   just setup
   ```

## Cursor (optional)

The enhancement backlog lives on **GitHub Issues** (label `grocery-wizard`). Agents should follow [AGENTS.md](AGENTS.md). Slash commands live in **`.cursor/commands/`** (committed). Requires `gh` for backlog commands. Do not commit `.cursor/mcp.json` (tokens).

`just setup` runs `streamlit skills` and links the same skill into `.cursor/skills/` for Cursor (gitignored symlinks into `.venv`).

# Execution

## Grocery Wizard UI

From the repository root (so `.streamlit/config.toml` theme applies):

```shell
just grocery-ui
# or: uv run python -m streamlit run src/grocery_wizard/ui/app.py
```

If you see `error: Failed to spawn: streamlit` even after `just setup`, the project `.venv` is usually stale (common after moving or cloning into a new path). Recreate it and start Streamlit as a module:

```shell
just refresh-venv
just grocery-ui
# or, on older main before Justfile uses -m streamlit:
uv run python -m streamlit run src/grocery_wizard/ui/app.py
```
