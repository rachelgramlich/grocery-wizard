"""Golden week fixture loaders (see tests/fixtures/golden_grocery_weeks/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.shopping.weekly_grocery_export import (
    export_grocery_lines_for_week_dict,
    recipes_from_week_dict,
)
from tests.repo_paths import FIXTURES_DIR

GOLDEN_WEEKS_DIR = FIXTURES_DIR / "golden_grocery_weeks"


def load_golden_week(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_golden_week_files() -> list[Path]:
    if not GOLDEN_WEEKS_DIR.is_dir():
        return []
    return sorted(GOLDEN_WEEKS_DIR.glob("*.json"))


def export_grocery_lines_for_week(week: dict[str, Any]) -> list[str]:
    return export_grocery_lines_for_week_dict(week)


def golden_week_recipes_for_apptest(week: dict[str, Any]) -> list[Recipe]:
    return recipes_from_week_dict(week)
