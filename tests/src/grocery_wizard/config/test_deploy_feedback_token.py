"""Deploy-time warnings for GitHub feedback PAT."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from src.grocery_wizard.config import warn_if_missing_github_feedback_token_when_deployed


@pytest.fixture(autouse=True)
def _clear_github_feedback_token_from_environ() -> None:
    """``_prime_config_environ`` uses setdefault; avoid leaking into other tests."""
    os.environ.pop("GITHUB_FEEDBACK_TOKEN", None)
    yield
    os.environ.pop("GITHUB_FEEDBACK_TOKEN", None)


def test_warns_when_auth_deploy_missing_feedback_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        """\
GROCERY_WIZARD_REQUIRE_AUTH = true
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.grocery_wizard.config._secrets_toml_path",
        lambda: secrets_path,
    )
    for key in ("GITHUB_FEEDBACK_TOKEN", "GROCERY_WIZARD_REQUIRE_AUTH"):
        monkeypatch.delenv(key, raising=False)

    with caplog.at_level(logging.WARNING):
        warn_if_missing_github_feedback_token_when_deployed()

    assert any("GITHUB_FEEDBACK_TOKEN is unset" in r.message for r in caplog.records)


def test_no_warn_when_token_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        """\
GROCERY_WIZARD_REQUIRE_AUTH = true
GITHUB_FEEDBACK_TOKEN = "github_pat_test"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.grocery_wizard.config._secrets_toml_path",
        lambda: secrets_path,
    )
    monkeypatch.delenv("GROCERY_WIZARD_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("GITHUB_FEEDBACK_TOKEN", raising=False)

    with caplog.at_level(logging.WARNING):
        warn_if_missing_github_feedback_token_when_deployed()

    assert not caplog.records


def test_no_warn_for_local_dev_without_auth(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("GROCERY_WIZARD_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("GITHUB_FEEDBACK_TOKEN", raising=False)
    monkeypatch.setenv("GROCERY_WIZARD_REQUIRE_AUTH", "false")

    with caplog.at_level(logging.WARNING):
        warn_if_missing_github_feedback_token_when_deployed()

    assert not caplog.records
