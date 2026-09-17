"""Removed CLI command names and user-facing migration hints."""

from __future__ import annotations

import sys

_STREAMLIT_HINT = "Use the Streamlit app (`just grocery-ui`) for meal planning and grocery lists."

_NYT_SYNC_HINT = (
    "Use the Streamlit app (`just grocery-ui`) — expand **Sync from NYT Cooking** "
    "under the title bar."
)

_ADD_RECIPE_HINT = "Use the Streamlit app (`just grocery-ui`) → **Add recipe**."

_EDIT_PANTRY_HINT = "Use the Streamlit app (`just grocery-ui`) → **Pantry & recurring**."

_DEV_HINT = "Agent workflow uses `gh` and `.cursor/commands/` (see AGENTS.md)."

_MAINTENANCE_REMOVED = (
    "Maintenance CLI was removed; edit ingredients in Notion or the Streamlit review step."
)

DEPRECATED_COMMANDS: dict[str, str] = {
    "add-recipe": _ADD_RECIPE_HINT,
    "edit-pantry": _EDIT_PANTRY_HINT,
    "dev": _DEV_HINT,
    "add": _ADD_RECIPE_HINT,
    "nyt": _NYT_SYNC_HINT,
    "plan": _STREAMLIT_HINT,
    "plan-recipes": _STREAMLIT_HINT,
    "grocery": _STREAMLIT_HINT,
    "create-grocery-list": _STREAMLIT_HINT,
    "pantry": _EDIT_PANTRY_HINT,
    "sync": _MAINTENANCE_REMOVED,
    "refresh-ingredients": _MAINTENANCE_REMOVED,
    "audit": "Maintenance CLI was removed.",
    "schema": "Maintenance CLI was removed.",
}

DEPRECATED_DEV_COMMANDS: dict[str, str] = {
    "backfill": _DEV_HINT,
    "reconcile": _DEV_HINT,
    "refresh-all": _DEV_HINT,
    "audit": _DEV_HINT,
    "schema": _DEV_HINT,
    "show-enhancement": _DEV_HINT,
    "work-on-enhancement": _DEV_HINT,
    "add-enhancement": _DEV_HINT,
    "report-bug": _DEV_HINT,
    "close-enhancement": _DEV_HINT,
    "spawn-enhancement-workers": _DEV_HINT,
    "install-cursor-commands": (
        "Slash commands live in `.cursor/commands/` (committed); no install step."
    ),
}


def deprecated_exit_code(argv: list[str]) -> int | None:
    """Return exit code 1 if argv uses a removed command, else None."""
    if not argv:
        return None

    if argv[0] in DEPRECATED_COMMANDS:
        print_deprecated(argv[0], DEPRECATED_COMMANDS[argv[0]])
        return 1

    if argv[0] == "dev":
        if len(argv) >= 2 and argv[1] in DEPRECATED_DEV_COMMANDS:
            print_deprecated(f"dev {argv[1]}", DEPRECATED_DEV_COMMANDS[argv[1]])
        else:
            print_deprecated("dev", _DEV_HINT)
        return 1

    return None


def print_deprecated(name: str, message: str) -> None:
    print(f"Command '{name}' was removed.", file=sys.stderr)
    print(message, file=sys.stderr)
    print("Run: just grocery-ui", file=sys.stderr)
