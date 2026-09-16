"""Argparse tree for NYT Cooking CLI (removed after #180)."""

from __future__ import annotations

import argparse

from src.grocery_wizard.cli.nyt_commands import register_nyt_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grocery-wizard",
        description="NYT Cooking integration (Streamlit is the primary workflow).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    nyt_parser = subparsers.add_parser(
        "nyt",
        help="NYT Cooking integration (saved recipes, sync to Notion)",
    )
    nyt_subparsers = nyt_parser.add_subparsers(dest="nyt_command", required=True)
    register_nyt_commands(nyt_subparsers)

    return parser
