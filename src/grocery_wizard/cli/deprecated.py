"""Removed CLI command names and user-facing migration hints."""

from __future__ import annotations

import sys

DEPRECATED_COMMANDS: dict[str, str] = {
    "add": "Use `add-recipe` instead.",
    "plan": "Use `plan-recipes` instead.",
    "grocery": "Use `create-grocery-list` instead.",
    "pantry": "Use `edit-pantry` instead.",
    "sync": "Use `dev backfill-ingredients` or `dev reconcile-ingredients`.",
    "refresh-ingredients": "Use `dev refresh-all-ingredients` instead.",
    "audit": "Use `dev audit-recipes` instead.",
    "schema": "Use `dev show-schema` instead.",
}

DEPRECATED_DEV_COMMANDS: dict[str, str] = {
    "backfill": "Use `dev backfill-ingredients` instead.",
    "reconcile": "Use `dev reconcile-ingredients` instead.",
    "refresh-all": "Use `dev refresh-all-ingredients` instead.",
    "audit": "Use `dev audit-recipes` instead.",
    "schema": "Use `dev show-schema` instead.",
    "show-enhancement": "Use `dev work-on-issue` instead.",
    "work-on-enhancement": "Use `dev work-on-issue` instead.",
    "add-enhancement": "Use `dev create-issues` instead.",
    "report-bug": "Use `dev create-issues` instead.",
    "close-enhancement": (
        "Merge a PR whose body includes `Closes #N` (do not close backlog issues by hand)."
    ),
    "spawn-enhancement-workers": (
        "Use `dev list-enhancements` and start one agent per issue."
    ),
    "install-cursor-commands": (
        "Slash commands live in `.cursor/commands/` (committed); no install step."
    ),
}


def deprecated_exit_code(argv: list[str]) -> int | None:
    """Return exit code 1 if argv uses a removed command, else None."""
    if argv and argv[0] in DEPRECATED_COMMANDS:
        print_deprecated(argv[0], DEPRECATED_COMMANDS[argv[0]])
        return 1

    if len(argv) >= 2 and argv[0] == "dev" and argv[1] in DEPRECATED_DEV_COMMANDS:
        print_deprecated(f"dev {argv[1]}", DEPRECATED_DEV_COMMANDS[argv[1]])
        return 1

    return None


def print_deprecated(name: str, message: str) -> None:
    print(f"Command '{name}' was removed.", file=sys.stderr)
    print(message, file=sys.stderr)
    print(
        "Run: uv run python -m src.grocery_wizard.cli --help",
        file=sys.stderr,
    )
