"""Tests for removed CLI command names and migration hints."""

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
        (["add-recipe"], "Add recipe"),
        (["edit-pantry"], "Pantry & recurring"),
        (["add"], "Add recipe"),
        (["pantry"], "Pantry & recurring"),
        (["dev"], "AGENTS.md"),
        (["dev", "backfill"], "AGENTS.md"),
        (["dev", "list-enhancements"], "AGENTS.md"),
        (["dev", "show-enhancement"], "AGENTS.md"),
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


def test_nyt_command_removed() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["nyt", "sync"])
    assert code == 1
    output = stderr.getvalue()
    assert "was removed" in output
    assert "Sync from NYT Cooking" in output


def test_unknown_command_exits_with_hint() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["not-a-command"])
    assert code == 1
    assert "just grocery-ui" in stderr.getvalue()
