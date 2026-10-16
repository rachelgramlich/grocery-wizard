"""Result model, ranking, flags, markdown rendering, and baseline comparison."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.grocery_wizard.dev.perf_audit.measure import RunStats

SCHEMA_VERSION = 1

TIER_P0_S = 5.0
TIER_P1_S = 2.0
TIER_P2_S = 1.0
HEAVY_ELEMENTS = 1500
HEAVY_OPTIONS = 2000
PYTHON_HEAVY_S = 1.0
READ_FANOUT = 6
WRITE_FANOUT = 3
COLD_GAP_MIN_S = 1.0
REGRESSION_PCT = 0.10
REGRESSION_ABS_S = 0.10

_CACHE_LEAK_EXEMPT = frozenset({"global.refresh"})

FLAG_HELP: dict[str, str] = {
    "P0": f"Over {TIER_P0_S:g}s warm: unacceptable, fix first",
    "P1": f"{TIER_P1_S:g}-{TIER_P0_S:g}s warm: feels slow",
    "P2": f"{TIER_P2_S:g}-{TIER_P1_S:g}s warm: noticeable",
    "CACHE_MISS_WARM": "Notion reads on a warm, non-write interaction (uncached or leaking cache)",
    "POST_WRITE_REFETCH": "A write cleared caches and the next render re-read Notion",
    "PYTHON_HEAVY": f"Over {PYTHON_HEAVY_S:g}s of non-network time (CPU in script or Streamlit)",
    "READ_FANOUT": f"{READ_FANOUT}+ Notion read requests in one interaction",
    "WRITE_FANOUT": f"{WRITE_FANOUT}+ Notion write requests in one interaction",
    "HEAVY_DOM": f"{HEAVY_ELEMENTS}+ elements or {HEAVY_OPTIONS}+ select options rendered",
    "COLD_GAP": "Cold run is 3x+ slower than warm and over 1s (first-load / cache-rebuild cost)",
    "EXTERNAL_ON_RENDER": "Non-Notion HTTP call (NYT, recipe sites) on a warm interaction",
}


@dataclass
class ScenarioResult:
    id: str
    page: str
    label: str
    writes: bool
    external: bool
    status: str = "ok"
    reason: str | None = None
    cold: RunStats | None = None
    warm: RunStats | None = None
    warm_runs_s: list[float] = field(default_factory=list)

    def headline(self) -> RunStats | None:
        return self.warm or self.cold

    def headline_s(self, write_latency_s: float) -> float:
        stats = self.headline()
        return stats.est_total_s(write_latency_s) if stats else 0.0


@dataclass
class AuditReport:
    meta: dict[str, Any]
    results: list[ScenarioResult]
    unmeasured_controls: list[str] = field(default_factory=list)
    write_latency_s: float = 0.35

    def ranked(self) -> list[ScenarioResult]:
        measured = [r for r in self.results if r.status == "ok" and (r.warm or r.cold)]
        return sorted(measured, key=lambda r: r.headline_s(self.write_latency_s), reverse=True)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "meta": self.meta,
            "write_latency_s": self.write_latency_s,
            "unmeasured_controls": self.unmeasured_controls,
            "results": [asdict(r) for r in self.results],
        }


def flags_for(result: ScenarioResult, write_latency_s: float) -> list[str]:
    stats = result.headline()
    if stats is None:
        return []
    flags: list[str] = []
    seconds = stats.est_total_s(write_latency_s)
    if seconds >= TIER_P0_S:
        flags.append("P0")
    elif seconds >= TIER_P1_S:
        flags.append("P1")
    elif seconds >= TIER_P2_S:
        flags.append("P2")
    if result.warm is not None:
        warm = result.warm
        if warm.notion_reads and not warm.notion_writes and result.id not in _CACHE_LEAK_EXEMPT:
            flags.append("CACHE_MISS_WARM")
        if warm.notion_reads and warm.notion_writes:
            flags.append("POST_WRITE_REFETCH")
    if stats.python_s >= PYTHON_HEAVY_S:
        flags.append("PYTHON_HEAVY")
    if stats.notion_reads >= READ_FANOUT:
        flags.append("READ_FANOUT")
    if stats.notion_writes >= WRITE_FANOUT:
        flags.append("WRITE_FANOUT")
    if stats.elements >= HEAVY_ELEMENTS or stats.options >= HEAVY_OPTIONS:
        flags.append("HEAVY_DOM")
    if (
        result.cold
        and result.warm
        and result.cold.wall_s >= COLD_GAP_MIN_S
        and result.cold.wall_s >= 3 * max(result.warm.wall_s, 0.05)
    ):
        flags.append("COLD_GAP")
    if result.warm is not None and result.warm.external_calls and not result.external:
        flags.append("EXTERNAL_ON_RENDER")
    return flags


def _fmt_s(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _rw(stats: RunStats | None) -> str:
    if stats is None:
        return "-"
    text = f"{stats.notion_reads}R/{stats.notion_writes}W"
    if stats.external_calls:
        text += f" +{stats.external_calls} ext"
    return text


def render_markdown(report: AuditReport, *, comparison: list[dict[str, Any]] | None = None) -> str:
    lat = report.write_latency_s
    meta = report.meta
    lines = [
        f"# Performance audit - {meta.get('timestamp', '')}",
        "",
        (
            f"- Commit: `{meta.get('git_sha', '?')}` | Streamlit {meta.get('streamlit', '?')} | "
            f"{meta.get('python', '?')}"
        ),
        (
            f"- Data size: {meta.get('recipes', '?')} recipes, "
            f"{meta.get('pantry_items', '?')} pantry items, "
            f"{meta.get('saved_plans', '?')} saved plans"
        ),
        (
            f"- Method: headless AppTest against live Notion. Reads are real and timed. Writes are "
            f"intercepted (never sent) and costed at **{lat:.2f}s each** in the est. column."
        ),
        "- Not included: browser paint / websocket time (confirm the top rows in a real browser).",
        "",
        "## Ranked: slowest first",
        "",
        "Time = warm run (server caches primed, fresh session); `est` adds stubbed-write cost.",
        "",
        (
            "| # | Scenario | Page | Warm est s | Warm s | Cold s | Notion warm | Python s | "
            "Elements / options | Flags |"
        ),
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for rank, result in enumerate(report.ranked(), start=1):
        stats = result.headline()
        assert stats is not None
        flag_text = ", ".join(flags_for(result, lat)) or "-"
        warm = result.warm
        lines.append(
            f"| {rank} | `{result.id}` {result.label} | {result.page} | "
            f"{stats.est_total_s(lat):.2f} | {_fmt_s(warm.wall_s if warm else None)} | "
            f"{_fmt_s(result.cold.wall_s if result.cold else None)} | {_rw(warm)} | "
            f"{stats.python_s:.2f} | {stats.elements} / {stats.options} | {flag_text} |"
        )

    lines += ["", "## Findings by flag", ""]
    by_flag: dict[str, list[str]] = {}
    for result in report.ranked():
        for flag in flags_for(result, lat):
            by_flag.setdefault(flag, []).append(result.id)
    for flag, help_text in FLAG_HELP.items():
        ids = by_flag.get(flag)
        if ids:
            lines.append(f"- **{flag}** ({help_text}): " + ", ".join(f"`{i}`" for i in ids))

    leaky = [r for r in report.ranked() if r.warm and r.warm.notion_by_endpoint]
    if leaky:
        lines += ["", "## Notion requests per interaction (warm)", ""]
        for result in leaky:
            assert result.warm is not None
            calls = ", ".join(f"{n}x {e}" for e, n in result.warm.notion_by_endpoint.items())
            lines.append(f"- `{result.id}`: {calls}")

    profiled = [r for r in report.ranked() if r.warm and r.warm.profile][:6]
    if profiled:
        lines += ["", "## Hot spots (cProfile, cumulative, repo + parser + Notion frames)", ""]
        for result in profiled:
            assert result.warm is not None
            lines += [f"### `{result.id}`", "", "```text", *(result.warm.profile or []), "```", ""]

    if report.unmeasured_controls:
        lines += ["", "## Coverage gaps (buttons seen but not in any scenario)", ""]
        lines += [f"- `{name}`" for name in report.unmeasured_controls]

    skipped = [r for r in report.results if r.status != "ok"]
    if skipped:
        lines += ["", "## Skipped / errored", ""]
        lines += [f"- `{r.id}` ({r.status}): {r.reason or ''}" for r in skipped]

    errored = [r for r in report.ranked() if (r.warm or r.cold) and (r.warm or r.cold).error]  # type: ignore[union-attr]
    if errored:
        lines += ["", "## Interactions that raised a Streamlit exception", ""]
        for result in errored:
            stats = result.warm or result.cold
            assert stats is not None
            lines.append(f"- `{result.id}`: {stats.error}")

    if comparison is not None:
        lines += ["", "## Comparison vs baseline", "", *render_comparison(comparison)]
    lines.append("")
    return "\n".join(lines)


def compare_reports(baseline: dict[str, Any], current: AuditReport) -> list[dict[str, Any]]:
    """Per-scenario warm/cold deltas against a previous ``to_json()`` payload."""
    base_by_id = {r["id"]: r for r in baseline.get("results", [])}
    base_lat = float(baseline.get("write_latency_s", current.write_latency_s))
    rows: list[dict[str, Any]] = []
    for result in current.results:
        stats = result.warm or result.cold
        old = base_by_id.get(result.id)
        if stats is None or old is None:
            continue
        old_stats = old.get("warm") or old.get("cold")
        if not old_stats:
            continue
        old_s = old_stats["wall_s"] + old_stats.get("notion_writes", 0) * base_lat
        new_s = stats.est_total_s(base_lat)
        delta = new_s - old_s
        pct = delta / old_s if old_s else 0.0
        verdict = "same"
        if delta > REGRESSION_ABS_S and pct > REGRESSION_PCT:
            verdict = "regressed"
        elif delta < -REGRESSION_ABS_S and pct < -REGRESSION_PCT:
            verdict = "improved"
        rows.append(
            {
                "id": result.id,
                "old_s": old_s,
                "new_s": new_s,
                "delta_s": delta,
                "pct": pct,
                "verdict": verdict,
            }
        )
    return sorted(rows, key=lambda row: row["delta_s"])


def render_comparison(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No overlapping scenarios with the baseline."]
    lines = [
        "| Scenario | Before s | After s | Delta s | Change | Verdict |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    lines += [
        f"| `{row['id']}` | {row['old_s']:.2f} | {row['new_s']:.2f} | {row['delta_s']:+.2f} | "
        f"{row['pct']:+.0%} | {row['verdict']} |"
        for row in rows
    ]
    return lines


_HEX_SUFFIX = re.compile(r"_[0-9a-f]{16}$")
_NUM_SUFFIX = re.compile(r"_\d+$")


def normalize_control(name: str) -> str:
    """Collapse per-item widget keys (``swap_meal_3``, ``pantry_rm_<hash>``) to a prefix."""
    if name.startswith("FormSubmitter:"):
        name = name.split("-", 1)[-1]
    stripped = _HEX_SUFFIX.sub("_", name)
    return _NUM_SUFFIX.sub("_", stripped)


def unmeasured(seen: set[str], covers: set[str]) -> list[str]:
    ignore = {"Log out"}
    gaps: list[str] = []
    for control in sorted(seen - ignore):
        if any(control == c or control.startswith(c) or c.startswith(control) for c in covers):
            continue
        gaps.append(control)
    return gaps


def save_report(
    report: AuditReport, out_dir: Path, *, comparison: list[dict[str, Any]] | None, stamp: str
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"perf-{stamp}.json"
    md_path = out_dir / f"perf-{stamp}.md"
    json_path.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, comparison=comparison), encoding="utf-8")
    (out_dir / "latest.json").write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    return json_path, md_path
