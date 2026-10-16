"""Timing, DOM-weight counting, and optional profiling for one interaction."""

from __future__ import annotations

import cProfile
import io
import pstats
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from src.grocery_wizard.dev.perf_audit.tap import NotionTap

_PROFILE_FILTER = r"(grocery_wizard|ingredient_parser|notion_client|nltk)"
_PROFILE_LINES = 14


@dataclass
class RunStats:
    """One measured interaction."""

    wall_s: float
    notion_reads: int = 0
    notion_read_s: float = 0.0
    notion_writes: int = 0
    notion_by_endpoint: dict[str, int] = field(default_factory=dict)
    external_calls: int = 0
    external_s: float = 0.0
    external_hosts: dict[str, int] = field(default_factory=dict)
    elements: int = 0
    options: int = 0
    error: str | None = None
    profile: list[str] | None = None

    @property
    def python_s(self) -> float:
        """Wall time not spent waiting on Notion or other HTTP reads (script CPU + Streamlit)."""
        return max(0.0, self.wall_s - self.notion_read_s - self.external_s)

    def est_total_s(self, write_latency_s: float) -> float:
        """Wall time plus estimated network cost of the stubbed writes."""
        return self.wall_s + self.notion_writes * write_latency_s


def _walk(node: Any) -> Iterator[Any]:
    children = getattr(node, "children", None)
    if isinstance(children, dict):
        for child in children.values():
            yield from _walk(child)
    else:
        yield node


def dom_weight(app: Any) -> tuple[int, int]:
    """Return ``(elements, select_options)`` currently rendered in the main area."""
    elements = 0
    options = 0
    for node in _walk(app.main):
        elements += 1
        raw = getattr(node, "options", None)
        if isinstance(raw, list | tuple):
            options += len(raw)
    return elements, options


def _profile_text(profiler: cProfile.Profile) -> list[str]:
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative").print_stats(_PROFILE_FILTER, _PROFILE_LINES)
    lines = [line.rstrip() for line in stream.getvalue().splitlines() if line.strip()]
    return lines[-(_PROFILE_LINES + 2) :]


def measure(
    act: Callable[[], Any],
    *,
    tap: NotionTap,
    profile: bool = False,
) -> tuple[RunStats, Any]:
    """Run ``act`` (which returns the AppTest) and collect timing, Notion tap data, DOM weight."""
    mark = tap.mark()
    profiler = cProfile.Profile() if profile else None
    start = time.perf_counter()
    error: str | None = None
    result: Any = None
    if profiler is not None:
        profiler.enable()
    try:
        result = act()
    finally:
        if profiler is not None:
            profiler.disable()
    wall = time.perf_counter() - start
    snapshot = tap.since(mark)

    elements = options = 0
    if result is not None:
        exceptions = list(getattr(result, "exception", []) or [])
        if exceptions:
            error = "; ".join(str(getattr(e, "value", e))[:160] for e in exceptions[:2])
        elements, options = dom_weight(result)

    stats = RunStats(
        wall_s=wall,
        notion_reads=snapshot.reads,
        notion_read_s=snapshot.read_seconds,
        notion_writes=snapshot.writes,
        notion_by_endpoint=snapshot.by_endpoint,
        external_calls=snapshot.external_calls,
        external_s=snapshot.external_seconds,
        external_hosts=snapshot.external_hosts,
        elements=elements,
        options=options,
        error=error,
        profile=_profile_text(profiler) if profiler is not None else None,
    )
    return stats, result
