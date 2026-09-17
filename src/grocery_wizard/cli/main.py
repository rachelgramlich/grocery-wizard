"""Grocery Wizard CLI — removed commands only (Streamlit + Notion is the product)."""

from __future__ import annotations

import sys

from src.grocery_wizard.cli.deprecated import deprecated_exit_code

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    deprecated_code = deprecated_exit_code(argv)
    if deprecated_code is not None:
        return deprecated_code

    print(
        "No CLI commands remain. Use `just grocery-ui` for Grocery Wizard.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
