"""Tests for CLI command names, deprecation messages, and help text."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest

from src.grocery_wizard.cli.main import main


@pytest.mark.parametrize(
    ("argv", "replacement"),
    [
        (["plan"], "grocery-ui"),
        (["plan-recipes"], "grocery-ui"),
        (["grocery"], "grocery-ui"),
        (["create-grocery-list"], "grocery-ui"),
        (["add"], "add-recipe"),
        (["pantry"], "edit-pantry"),
        (["dev", "backfill"], "backfill-ingredients"),
        (["dev", "reconcile"], "reconcile-ingredients"),
        (["dev", "refresh-all"], "refresh-all-ingredients"),
        (["dev", "audit"], "audit-recipes"),
        (["dev", "schema"], "show-schema"),
        (["dev", "show-enhancement"], "work-on-issue"),
        (["dev", "work-on-enhancement"], "work-on-issue"),
        (["dev", "add-enhancement"], "create-issues"),
        (["dev", "spawn-enhancement-workers"], "list-enhancements"),
    ],
)
def test_deprecated_commands_print_replacement(argv: list[str], replacement: str) -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(argv)
    assert code == 1
    output = stderr.getvalue()
    assert replacement in output
    assert "was removed" in output


def test_main_prompts_feedback_after_successful_prod_command() -> None:
    with (
        patch("src.grocery_wizard.cli.prod_commands.cmd_add", return_value=0),
        patch("src.grocery_wizard.cli.main.prompt_for_feedback") as prompt_mock,
    ):
        code = main(["add-recipe", "https://example.com/r"])

    assert code == 0
    prompt_mock.assert_called_once_with("add-recipe")


def test_main_skips_feedback_on_failure() -> None:
    with (
        patch("src.grocery_wizard.cli.prod_commands.cmd_add", return_value=1),
        patch("src.grocery_wizard.cli.main.prompt_for_feedback") as prompt_mock,
    ):
        code = main(["add-recipe"])

    assert code == 1
    prompt_mock.assert_not_called()


def test_main_skips_feedback_for_dev_commands() -> None:
    with (
        patch("src.grocery_wizard.cli.dev_commands.cmd_dev_list_feedback", return_value=0),
        patch("src.grocery_wizard.cli.main.prompt_for_feedback") as prompt_mock,
    ):
        code = main(["dev", "list-feedback"])

    assert code == 0
    prompt_mock.assert_not_called()


def test_dev_list_feedback_prints_entries(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("src.grocery_wizard.lib.feedback.list_feedback", return_value="[ts] plan: ok"):
        code = main(["dev", "list-feedback"])

    assert code == 0
    assert "[ts] plan: ok" in capsys.readouterr().out


def test_nyt_command_removed(capsys: pytest.CaptureFixture[str]) -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["nyt", "sync"])
    assert code == 1
    output = stderr.getvalue()
    assert "was removed" in output
    assert "Sync from NYT Cooking" in output
