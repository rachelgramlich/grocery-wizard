"""Tests for NYT CLI help text (prod/dev CLI removed in #179)."""

from __future__ import annotations

import pytest

from src.grocery_wizard.cli.main import main


def test_nyt_help_lists_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["nyt", "--help"])
    output = capsys.readouterr().out
    assert "auth-status" in output
    assert "sync" in output


def test_nyt_sync_help_lists_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["nyt", "sync", "--help"])
    output = capsys.readouterr().out
    assert "--collection" in output
    assert "--dry-run" in output
    assert "--confirm" in output
