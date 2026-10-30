"""Tests for grocery list debug log writer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.grocery_wizard.shopping.list_log import (
    MAX_LIST_LOGS,
    OUTCOME_KEPT,
    OUTCOME_PANTRY,
    SOURCE_RECIPE,
    ListTrace,
    apply_adjustments,
    build_list_log,
    latest_list_log_path,
    write_list_log,
)


def test_build_list_log_tracks_sources_and_skipped() -> None:
    trace = ListTrace()
    trace.start_recipe("Tacos", "2 tsp chili powder\n1 avocado", ingredient_source="notion")
    trace.record_line(
        "Tacos",
        "2 tsp chili powder",
        outcome=OUTCOME_PANTRY,
        item="chili powder",
    )
    trace.record_line(
        "Tacos",
        "1 avocado",
        outcome=OUTCOME_KEPT,
        item="avocado",
        amount=None,
    )
    log = build_list_log(
        trace,
        meals=["Tacos"],
        exclude_pantry=True,
        excluded_pantry=["chili powder"],
        missing_ingredients=[],
        item_provenance={"avocado": ["Tacos"]},
        extra_items=[],
        final_items=["avocado"],
        created_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
    )
    assert log["meals"][0]["name"] == "Tacos"
    assert log["pantry_excluded"] == ["chili powder"]
    assert log["final_list"] == [
        {
            "item": "avocado",
            "aisle": log["final_list"][0]["aisle"],
            "source": SOURCE_RECIPE,
            "recipes": ["Tacos"],
        }
    ]
    skipped = {entry["line"] for entry in log["skipped"]}
    assert "2 tsp chili powder" in skipped


def test_write_list_log_prunes_old_files(tmp_path: Path) -> None:
    history = tmp_path / "list_history"
    keep = 3
    paths: list[Path] = []
    for index in range(keep + 2):
        log = {
            "created_at": datetime(2026, 10, 30, 12, index, tzinfo=UTC).isoformat(),
            "final_list": [],
        }
        path = write_list_log(log, history_dir=history, keep=keep)
        assert path is not None
        paths.append(path)
    remaining = sorted(history.glob("*.json"))
    assert len(remaining) == keep
    assert latest_list_log_path(history) == remaining[-1]


def test_apply_adjustments_updates_final_list() -> None:
    base = {
        "final_list": [
            {"item": "avocado", "aisle": "Vegetables", "source": "recipe", "recipes": ["Tacos"]}
        ],
        "user_adjustments": {"pantry_readded": [], "removed_once": []},
    }
    updated = apply_adjustments(
        base,
        final_items=["avocado", "salt"],
        readd=["salt"],
        removed_once=[],
    )
    sources = {entry["item"]: entry["source"] for entry in updated["final_list"]}
    assert sources["avocado"] == "recipe"
    assert sources["salt"] == "pantry_readd"


def test_write_list_log_json_roundtrip(tmp_path: Path) -> None:
    trace = ListTrace()
    log = build_list_log(
        trace,
        meals=[],
        exclude_pantry=False,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=[],
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    path = write_list_log(log, history_dir=tmp_path, keep=MAX_LIST_LOGS)
    assert path is not None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == log["schema_version"]
