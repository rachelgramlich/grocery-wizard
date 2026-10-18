"""CLI: ``just performance-audit`` (see ``docs/performance-audit.md``)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.grocery_wizard.dev.perf_audit.report import (
    compare_reports,
    save_report,
)
from src.grocery_wizard.dev.perf_audit.runner import run_audit, select_scenarios

DEFAULT_OUT_DIR = Path(".local/grocery_wizard/perf")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="performance-audit",
        description="Time every Streamlit control against live Notion (writes are stubbed).",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="PATTERN",
        help="Run scenarios whose id matches (glob or substring); repeatable.",
    )
    parser.add_argument("--list", action="store_true", help="List scenario ids and exit.")
    parser.add_argument("--reps", type=int, default=2, help="Warm repetitions (median is used).")
    parser.add_argument("--skip-cold", action="store_true", help="Skip the cold-cache run.")
    parser.add_argument(
        "--profile", action="store_true", help="cProfile the first warm run of each scenario."
    )
    parser.add_argument(
        "--write-latency",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Cost to assume per stubbed Notion write (default: 0.4).",
    )
    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Do not block non-Notion HTTP calls (NYT, recipe sites).",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR, help="Report directory.")
    parser.add_argument(
        "--compare",
        metavar="PATH|latest",
        help="Diff against an earlier JSON report (or 'latest').",
    )
    parser.add_argument(
        "--fail-over",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Exit 1 if any warm scenario exceeds this many seconds.",
    )
    return parser


def _load_baseline(spec: str | None, out_dir: Path) -> dict | None:
    if not spec:
        return None
    path = out_dir / "latest.json" if spec == "latest" else Path(spec)
    if not path.is_file():
        sys.stderr.write(f"No baseline at {path}; skipping comparison.\n")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    scenarios = select_scenarios(args.only)
    if args.list:
        for scenario in scenarios:
            marks = ("W" if scenario.writes else "-") + ("X" if scenario.external else "-")
            sys.stdout.write(f"{marks}  {scenario.id:44s} {scenario.label}\n")
        return 0
    if not scenarios:
        sys.stderr.write("No scenarios matched --only.\n")
        return 2

    logging.getLogger("streamlit").setLevel(logging.ERROR)
    baseline = _load_baseline(args.compare, args.out)

    report = run_audit(
        scenarios,
        reps=args.reps,
        do_cold=not args.skip_cold,
        profile=args.profile,
        write_latency_s=args.write_latency,
        allow_external=args.allow_external,
        progress=lambda msg: sys.stderr.write(msg + "\n"),
    )
    comparison = compare_reports(baseline, report) if baseline else None
    stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    json_path, md_path = save_report(report, args.out, comparison=comparison, stamp=stamp)

    sys.stdout.write(md_path.read_text(encoding="utf-8"))
    sys.stdout.write(f"\nSaved: {md_path}\n       {json_path}\n")

    if args.fail_over is not None:
        worst = max((r.headline_s(report.write_latency_s) for r in report.ranked()), default=0.0)
        if worst > args.fail_over:
            sys.stderr.write(f"FAIL: slowest warm scenario {worst:.2f}s > {args.fail_over:.2f}s\n")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
