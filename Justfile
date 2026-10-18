# Justfile for grocery-wizard

set dotenv-load

# Default recipe to show help
default:
    @just --list

# Setup: Install Python dependencies and Streamlit agent skills (for Cursor / UI work)
setup:
    uv sync --all-extras --group dev
    uv run streamlit skills --yes
    mkdir -p .cursor/skills
    ln -sfn "$(readlink .agents/skills/developing-with-streamlit)" .cursor/skills/developing-with-streamlit

# Upgrade and sync dependencies
setup-upgrade:
    uv sync --upgrade

# Install Python dependencies only (no Streamlit skills symlink)
sync:
    uv sync --all-extras --group dev

# Lint (no auto-fix; same as CI)
lint-check:
    uv run ruff check

# Verify formatting (no write; same as CI)
format-check:
    uv run ruff format --check

# Run linting checks with auto-fix
lint:
    uv run ruff check --fix

# Format code
format:
    uv run ruff format

# Run tests
test:
    uv run pytest

# Headless holistic UI smoke (AppTest; mocked Notion — same cases run in full pytest / CI)
smoke-ui:
    uv run pytest -m holistic_ui_smoke

# Run tests with coverage
test-cov:
    uv run pytest --cov=. --cov-report=html

# Symlink .streamlit/secrets.toml → repo-root secrets.toml (for st.login [auth])
link-secrets:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .streamlit
    if [[ -f secrets.toml ]]; then
      ln -sf ../secrets.toml .streamlit/secrets.toml
      echo "Linked .streamlit/secrets.toml → secrets.toml"
    else
      echo "No secrets.toml at repo root — copy secrets.toml.example first" >&2
      exit 1
    fi

# Run Grocery Wizard Streamlit UI (laptop / same-WiFi phone)
grocery-ui *ARGS:
    just link-secrets
    uv run streamlit run src/grocery_wizard/ui/app.py {{ARGS}}

# Push store_aisles.txt labels to Notion pantry Store Aisle options and remap rows
sync-pantry-aisles:
    PYTHONPATH=src uv run python -c "from grocery_wizard.integrations.notion_pantry_setup import sync_pantry_section_store_aisles; r = sync_pantry_section_store_aisles(); print(f'Updated {len(r.aisle_labels)} aisle options; remapped {r.rows_migrated} rows.')"

# Time every Streamlit control against live Notion (writes stubbed); see docs/performance-audit.md
performance-audit *ARGS:
    uv run python -m src.grocery_wizard.dev.perf_audit {{ARGS}}

# Alias for scripts/docs that still say perf-audit
perf-audit *ARGS:
    @just performance-audit {{ARGS}}

# Clean up Python cache files
clean:
    find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -r {} + 2>/dev/null || true
    find . -type d -name .mypy_cache -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf .coverage htmlcov/
    rm -rf dist/ build/ *.egg-info

# Local pre-push: ruff lint + format check + tests (no auto-fix)
check: lint-check format-check test

# GitHub Actions entry point (sync + same checks as check)
ci: sync lint-check format-check test

# Run pre-commit checks
pre-commit:
    uv run pre-commit run --all-files

# Full development setup
dev-setup: setup format lint test
    @echo "Development setup complete!"

# Show Python version and environment info
info:
    @echo "Python version:"
    @uv run python --version
    @echo "\nPython location:"
    @uv run which python
    @echo "\nInstalled packages:"
    @uv pip list
