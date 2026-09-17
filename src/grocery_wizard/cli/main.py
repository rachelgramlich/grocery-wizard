"""Grocery Wizard CLI — production workflow and dev maintenance commands."""

from __future__ import annotations

import sys

from src.grocery_wizard.cli.deprecated import deprecated_exit_code
from src.grocery_wizard.cli.dev_commands import (
    cmd_dev_audit,
    cmd_dev_backfill,
    cmd_dev_backfill_enhancement_labels,
    cmd_dev_create_issues,
    cmd_dev_enhancement_pr_title,
    cmd_dev_list_enhancements,
    cmd_dev_list_feedback,
    cmd_dev_migrate_enhancements_to_github,
    cmd_dev_reconcile,
    cmd_dev_record_manual_verification,
    cmd_dev_reformat,
    cmd_dev_refresh_all,
    cmd_dev_remap_notion_pantry_aisles,
    cmd_dev_schema,
    cmd_dev_suggest_fixes,
    cmd_dev_sync_notion_pantry_sections,
    cmd_dev_validate_pipeline,
    cmd_dev_work_on_issue,
)
from src.grocery_wizard.cli.parser import build_parser
from src.grocery_wizard.cli.prod_commands import cmd_add, cmd_pantry
from src.grocery_wizard.lib.feedback import PROD_COMMANDS, prompt_for_feedback

__all__ = [
    "cmd_add",
    "cmd_dev_audit",
    "cmd_dev_backfill",
    "cmd_dev_backfill_enhancement_labels",
    "cmd_dev_create_issues",
    "cmd_dev_enhancement_pr_title",
    "cmd_dev_list_enhancements",
    "cmd_dev_list_feedback",
    "cmd_dev_migrate_enhancements_to_github",
    "cmd_dev_reconcile",
    "cmd_dev_record_manual_verification",
    "cmd_dev_reformat",
    "cmd_dev_refresh_all",
    "cmd_dev_remap_notion_pantry_aisles",
    "cmd_dev_schema",
    "cmd_dev_suggest_fixes",
    "cmd_dev_sync_notion_pantry_sections",
    "cmd_dev_validate_pipeline",
    "cmd_dev_work_on_issue",
    "cmd_pantry",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    deprecated_code = deprecated_exit_code(argv)
    if deprecated_code is not None:
        return deprecated_code

    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    if exit_code == 0 and args.command in PROD_COMMANDS:
        prompt_for_feedback(args.command)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
