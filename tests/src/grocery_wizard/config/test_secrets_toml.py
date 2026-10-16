"""Config loading from repo-root ``secrets.toml``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.grocery_wizard.config import load_auth_gate_settings, load_config


def test_load_config_reads_flat_secrets_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        """\
NOTION_API_KEY = "from-secrets"
NOTION_RECIPE_DATABASE_ID = "00000000-0000-4000-8000-000000000001"
NOTION_PANTRY_DATABASE_ID = "00000000-0000-4000-8000-000000000002"
NOTION_RECURRING_WEEKLY_DATABASE_ID = "00000000-0000-4000-8000-000000000003"
NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID = "00000000-0000-4000-8000-000000000004"
GITHUB_FEEDBACK_TOKEN = "gh-test"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTION_API_KEY", "from-env")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.grocery_wizard.config._secrets_toml_path",
        lambda: secrets_path,
    )
    for key in list(os.environ):
        if key.startswith("NOTION_") and key != "NOTION_API_KEY":
            monkeypatch.delenv(key, raising=False)

    cfg = load_config()
    assert cfg.notion_api_key == "from-env"
    assert cfg.github_feedback_token == "gh-test"


def test_load_auth_gate_settings_without_notion_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        """\
GROCERY_WIZARD_REQUIRE_AUTH = true
GROCERY_WIZARD_AUTH_EMAIL_ALLOWLIST = "a@example.com"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.grocery_wizard.config._secrets_toml_path",
        lambda: secrets_path,
    )
    for key in list(os.environ):
        if key.startswith("NOTION_"):
            monkeypatch.delenv(key, raising=False)

    gate = load_auth_gate_settings()
    assert gate.require_auth is True
    assert gate.auth_email_allowlist == "a@example.com"

    for key in ("GROCERY_WIZARD_REQUIRE_AUTH", "GROCERY_WIZARD_AUTH_EMAIL_ALLOWLIST"):
        monkeypatch.delenv(key, raising=False)
