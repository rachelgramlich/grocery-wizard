"""Argparse tree for the grocery-wizard CLI."""

from __future__ import annotations

import argparse

from src.grocery_wizard.cli.dev_commands import register_dev_commands
from src.grocery_wizard.cli.prod_commands import register_prod_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grocery-wizard",
        description="Add recipes, edit pantry, and dev maintenance (Streamlit for planning).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_prod_commands(subparsers)

    dev_parser = subparsers.add_parser(
        "dev",
        help="Database maintenance and debugging commands",
    )
    dev_subparsers = dev_parser.add_subparsers(dest="dev_command", required=True)
    register_dev_commands(dev_subparsers)

    return parser
