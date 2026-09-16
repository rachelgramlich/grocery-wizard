"""NYT Cooking CLI only (temporary until Streamlit NYT sync in #180)."""

from __future__ import annotations

import sys

from src.grocery_wizard.cli.nyt_commands import (
    cmd_nyt_apply_metadata,
    cmd_nyt_auth_status,
    cmd_nyt_reclassify,
    cmd_nyt_review_metadata,
    cmd_nyt_saved,
    cmd_nyt_sync,
)
from src.grocery_wizard.cli.parser import build_parser

__all__ = [
    "cmd_nyt_apply_metadata",
    "cmd_nyt_auth_status",
    "cmd_nyt_reclassify",
    "cmd_nyt_review_metadata",
    "cmd_nyt_saved",
    "cmd_nyt_sync",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
