"""Run scenarios cold and warm, aggregate results, and gather coverage data."""

from __future__ import annotations

import statistics
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from fnmatch import fnmatch
from typing import Any

import streamlit as st

from src.grocery_wizard.dev.perf_audit.flows import AuditContext, ScenarioSkipError
from src.grocery_wizard.dev.perf_audit.measure import RunStats, measure
from src.grocery_wizard.dev.perf_audit.report import (
    AuditReport,
    ScenarioResult,
    normalize_control,
    unmeasured,
)
from src.grocery_wizard.dev.perf_audit.scenarios import Scenario, build_scenarios
from src.grocery_wizard.dev.perf_audit.tap import DEFAULT_WRITE_LATENCY_S, NotionTap


def select_scenarios(patterns: list[str] | None) -> list[Scenario]:
    scenarios = build_scenarios()
    if not patterns:
        return scenarios
    return [s for s in scenarios if any(fnmatch(s.id, p) or p in s.id for p in patterns)]


def clear_server_caches() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def _collect_meta(tap: NotionTap) -> dict[str, Any]:
    mark = tap.mark()
    meta: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "git_sha": _git_sha(),
        "streamlit": st.__version__,
        "python": f"Python {sys.version_info.major}.{sys.version_info.minor}",
    }
    try:
        from src.grocery_wizard.config import load_config
        from src.grocery_wizard.integrations.notion_household import NotionPantryDB
        from src.grocery_wizard.planning.saved_weekly_plans import list_saved_plans
        from src.grocery_wizard.ui.db_access import get_db

        db = get_db()
        meta["recipes"] = len(db.query_recipes())
        meta["pantry_items"] = len(NotionPantryDB().list_entries())
        meta["saved_plans"] = len(list_saved_plans(recipes_db=db))
        meta["notion_recipe_db"] = load_config().notion_recipe_database_id[-6:]
    except Exception as exc:
        meta["data_size_error"] = str(exc)[:120]
    del mark
    return meta


def _observe_controls(app: Any, seen: set[str]) -> None:
    for widget in getattr(app, "button", []) or []:
        key = getattr(widget, "key", None)
        seen.add(normalize_control(str(key or widget.label)))


def _run_once(
    scenario: Scenario,
    ctx: AuditContext,
    tap: NotionTap,
    seen: set[str],
    *,
    clear_before_act: bool,
    profile: bool,
) -> RunStats:
    app = scenario.prepare(ctx)
    _observe_controls(app, seen)
    if clear_before_act:
        clear_server_caches()
    stats, result = measure(lambda: scenario.act(ctx, app), tap=tap, profile=profile)
    if result is not None:
        _observe_controls(result, seen)
    return stats


def run_scenario(
    scenario: Scenario,
    ctx: AuditContext,
    tap: NotionTap,
    seen: set[str],
    *,
    reps: int,
    do_cold: bool,
    profile: bool,
) -> ScenarioResult:
    result = ScenarioResult(
        id=scenario.id,
        page=scenario.page,
        label=scenario.label,
        writes=scenario.writes,
        external=scenario.external,
    )
    try:
        if do_cold:
            result.cold = _run_once(scenario, ctx, tap, seen, clear_before_act=True, profile=False)
        else:
            _run_once(scenario, ctx, tap, seen, clear_before_act=False, profile=False)
        warm_runs: list[RunStats] = [
            _run_once(
                scenario,
                ctx,
                tap,
                seen,
                clear_before_act=False,
                profile=profile and index == 0,
            )
            for index in range(max(1, reps))
        ]
    except ScenarioSkipError as exc:
        result.status = "skipped"
        result.reason = str(exc)
        return result
    except Exception as exc:
        result.status = "error"
        result.reason = f"{type(exc).__name__}: {str(exc)[:200]}"
        return result

    result.warm_runs_s = [r.wall_s for r in warm_runs]
    median_wall = statistics.median(result.warm_runs_s)
    result.warm = min(warm_runs, key=lambda r: abs(r.wall_s - median_wall))
    if profile:
        result.warm.profile = warm_runs[0].profile
    return result


def run_audit(
    scenarios: list[Scenario],
    *,
    reps: int = 2,
    do_cold: bool = True,
    profile: bool = False,
    write_latency_s: float | None = None,
    allow_external: bool = False,
    progress: Callable[[str], None] | None = None,
) -> AuditReport:
    say = progress or (lambda _msg: None)
    tap = NotionTap(stub_writes=True, allow_external=allow_external)
    tap.install()
    try:
        ctx = AuditContext()
        meta = _collect_meta(tap)
        seen: set[str] = set()
        results: list[ScenarioResult] = []
        for index, scenario in enumerate(scenarios, start=1):
            say(f"[{index}/{len(scenarios)}] {scenario.id}")
            results.append(
                run_scenario(scenario, ctx, tap, seen, reps=reps, do_cold=do_cold, profile=profile)
            )
        latency = write_latency_s if write_latency_s is not None else DEFAULT_WRITE_LATENCY_S
        covers = {c for s in build_scenarios() for c in s.covers}
        report = AuditReport(
            meta=meta,
            results=results,
            unmeasured_controls=unmeasured(seen, covers),
            write_latency_s=round(latency, 3),
        )
    finally:
        tap.uninstall()
    report.meta["safe_mode"] = "Notion writes stubbed; mutating external HTTP blocked"
    return report
