"""Unit tests for the pure parts of the perf-audit harness (no Notion, no Streamlit run)."""

from __future__ import annotations

import pytest

from src.grocery_wizard.dev.perf_audit.measure import RunStats
from src.grocery_wizard.dev.perf_audit.report import (
    AuditReport,
    ScenarioResult,
    compare_reports,
    flags_for,
    normalize_control,
    render_markdown,
    unmeasured,
)
from src.grocery_wizard.dev.perf_audit.runner import select_scenarios
from src.grocery_wizard.dev.perf_audit.scenarios import build_scenarios
from src.grocery_wizard.dev.perf_audit.tap import (
    is_write_request,
    normalize_endpoint,
    stub_write_response,
)

PAGE_ID = "12345678-1234-1234-1234-123456789abc"


def _result(
    scenario_id: str,
    *,
    warm: RunStats | None,
    cold: RunStats | None = None,
    writes: bool = False,
) -> ScenarioResult:
    return ScenarioResult(
        id=scenario_id,
        page="weekly",
        label="label",
        writes=writes,
        external=False,
        warm=warm,
        cold=cold,
    )


def test_normalize_endpoint_replaces_ids() -> None:
    assert (
        normalize_endpoint("post", f"/data_sources/{PAGE_ID}/query?x=1")
        == "POST /data_sources/{id}/query"
    )


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("GET", "/databases/abc", False),
        ("POST", f"/data_sources/{PAGE_ID}/query", False),
        ("POST", "/search", False),
        ("POST", "/pages", True),
        ("PATCH", f"/pages/{PAGE_ID}", True),
        ("PATCH", f"/views/{PAGE_ID}", True),
        ("DELETE", f"/blocks/{PAGE_ID}", True),
    ],
)
def test_is_write_request(method: str, path: str, expected: bool) -> None:
    assert is_write_request(method, path) is expected


def test_stub_write_response_echoes_properties_in_response_shape() -> None:
    body = {
        "properties": {
            "Name": {"title": [{"text": {"content": "2026-10-18_plan"}}]},
            "Week": {"date": {"start": "2026-10-18"}},
        }
    }
    response = stub_write_response("POST", "/pages", body)
    assert response["object"] == "page"
    name = response["properties"]["Name"]
    assert name["type"] == "title"
    assert name["title"][0]["plain_text"] == "2026-10-18_plan"
    assert response["properties"]["Week"]["date"]["start"] == "2026-10-18"


def test_stub_write_response_keeps_page_id_for_updates() -> None:
    response = stub_write_response("PATCH", f"/pages/{PAGE_ID}", {"properties": {}})
    assert response["id"] == PAGE_ID


def test_run_stats_estimates_write_cost_and_python_time() -> None:
    stats = RunStats(wall_s=2.0, notion_reads=3, notion_read_s=0.5, notion_writes=2, external_s=0.5)
    assert stats.python_s == pytest.approx(1.0)
    assert stats.est_total_s(0.4) == pytest.approx(2.8)


def test_flags_tier_and_cache_leak() -> None:
    slow = RunStats(wall_s=6.0, notion_reads=2, notion_read_s=1.0)
    flags = flags_for(_result("weekly.x", warm=slow), 0.4)
    assert "P0" in flags
    assert "CACHE_MISS_WARM" in flags
    assert "PYTHON_HEAVY" in flags


def test_flags_post_write_refetch_is_not_cache_leak() -> None:
    stats = RunStats(wall_s=1.5, notion_reads=3, notion_read_s=0.5, notion_writes=1)
    flags = flags_for(_result("pantry.add", warm=stats, writes=True), 0.4)
    assert "POST_WRITE_REFETCH" in flags
    assert "CACHE_MISS_WARM" not in flags


def test_flags_cold_gap_needs_meaningful_cold_time() -> None:
    quick = _result("a", warm=RunStats(wall_s=0.01), cold=RunStats(wall_s=0.3))
    assert "COLD_GAP" not in flags_for(quick, 0.4)
    slow = _result("b", warm=RunStats(wall_s=0.2), cold=RunStats(wall_s=3.0))
    assert "COLD_GAP" in flags_for(slow, 0.4)


def test_ranking_is_slowest_first_and_skips_unmeasured() -> None:
    report = AuditReport(
        meta={},
        results=[
            _result("fast", warm=RunStats(wall_s=0.1)),
            _result("slow", warm=RunStats(wall_s=9.0)),
            ScenarioResult(
                "skipped", "weekly", "x", writes=False, external=False, status="skipped"
            ),
        ],
    )
    assert [r.id for r in report.ranked()] == ["slow", "fast"]
    markdown = render_markdown(report)
    assert markdown.index("`slow`") < markdown.index("`fast`")
    assert "skipped" in markdown


def test_compare_reports_marks_improvements_and_regressions() -> None:
    baseline = AuditReport(
        meta={},
        results=[
            _result("a", warm=RunStats(wall_s=10.0)),
            _result("b", warm=RunStats(wall_s=1.0)),
            _result("c", warm=RunStats(wall_s=1.0)),
        ],
    ).to_json()
    current = AuditReport(
        meta={},
        results=[
            _result("a", warm=RunStats(wall_s=1.0)),
            _result("b", warm=RunStats(wall_s=3.0)),
            _result("c", warm=RunStats(wall_s=1.02)),
        ],
    )
    verdicts = {row["id"]: row["verdict"] for row in compare_reports(baseline, current)}
    assert verdicts == {"a": "improved", "b": "regressed", "c": "same"}


def test_normalize_control_collapses_dynamic_keys() -> None:
    assert normalize_control("swap_meal_3") == "swap_meal_"
    assert normalize_control("pantry_rm_0123456789abcdef") == "pantry_rm_"
    assert normalize_control("FormSubmitter:pantry_add_form-Add to pantry") == "Add to pantry"
    assert normalize_control("build_plan") == "build_plan"


def test_unmeasured_reports_only_uncovered_controls() -> None:
    seen = {"build_plan", "swap_meal_", "mystery_button", "Log out"}
    assert unmeasured(seen, {"build_plan", "swap_meal_"}) == ["mystery_button"]


def test_scenario_catalogue_ids_are_unique_and_cover_every_page() -> None:
    scenarios = build_scenarios()
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids))
    assert {s.page for s in scenarios} == {"global", "weekly", "add", "pantry", "maintenance"}


def test_select_scenarios_filters_by_glob_and_substring() -> None:
    assert {s.id for s in select_scenarios(["pantry.*"])} == {
        s.id for s in build_scenarios() if s.id.startswith("pantry.")
    }
    assert [s.id for s in select_scenarios(["build_plan"])] == ["weekly.meals.build_plan"]


def test_noisy_flag_marks_unstable_warm_repetitions() -> None:
    from src.grocery_wizard.dev.perf_audit.measure import RunStats
    from src.grocery_wizard.dev.perf_audit.report import ScenarioResult, flags_for

    stable = ScenarioResult(
        id="a",
        page="p",
        label="l",
        writes=False,
        external=False,
        warm=RunStats(wall_s=1.0),
        warm_runs_s=[1.0, 1.1, 1.2],
    )
    noisy = ScenarioResult(
        id="b",
        page="p",
        label="l",
        writes=False,
        external=False,
        warm=RunStats(wall_s=1.0),
        warm_runs_s=[1.0, 1.2, 9.0],
    )
    assert "NOISY" not in flags_for(stable, 0.4)
    assert "NOISY" in flags_for(noisy, 0.4)
