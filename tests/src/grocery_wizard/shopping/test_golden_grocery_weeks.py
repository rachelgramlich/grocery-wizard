"""Golden weekly plans: full UI-equivalent grocery pipeline, not single-line normalize cases."""

from __future__ import annotations

import pytest

from src.grocery_wizard.shopping.grocery_invariants import assert_grocery_list_invariants
from tests.src.grocery_wizard.shopping.golden_week_harness import (
    export_grocery_lines_for_week,
    iter_golden_week_files,
    load_golden_week,
)

pytestmark = pytest.mark.golden_grocery


@pytest.fixture(params=list(iter_golden_week_files()), ids=lambda p: p.stem)
def golden_week_file(request: pytest.FixtureRequest):
    return request.param


def test_golden_week_export_matches_snapshot(golden_week_file) -> None:
    week = load_golden_week(golden_week_file)
    expected = week.get("expect_grocery_lines")
    assert expected is not None, f"{golden_week_file.name}: missing expect_grocery_lines"

    actual = export_grocery_lines_for_week(week)
    assert actual == expected, (
        f"Golden week {week['id']!r} export changed.\n"
        "If intentional, refresh expect_grocery_lines (see docs/grocery-quality.md)."
    )


def test_golden_week_export_passes_invariants(golden_week_file) -> None:
    week = load_golden_week(golden_week_file)
    lines = export_grocery_lines_for_week(week)
    assert_grocery_list_invariants(lines)
