"""Tests for week_plan_store loaders."""

from __future__ import annotations

from pathlib import Path

from src.grocery_wizard.planning.meal_planner import save_week_plan
from src.grocery_wizard.planning.week_plan_store import (
    load_current_week_plan_from_file,
    load_week_plan_names,
)


def test_load_week_plan_names_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "week_plan.json"
    save_week_plan(["A", "B"], path)
    assert load_week_plan_names(path) == ["A", "B"]


def test_load_current_week_plan_from_file(tmp_path: Path) -> None:
    path = tmp_path / "week_plan.json"
    save_week_plan(["Soup"], path)
    loaded = load_current_week_plan_from_file(path)
    assert loaded is not None
    assert loaded.recipe_names == ("Soup",)
    assert "week plan" in loaded.source_label


def test_load_current_week_plan_from_file_missing(tmp_path: Path) -> None:
    assert load_current_week_plan_from_file(tmp_path / "missing.json") is None
