"""Load and persist the current week's meal plan (local file + documented sources).

Authority when CLI and Notion saved plans coexist
-------------------------------------------------

**Streamlit UI (in-session):** ``plan_meals_text`` session state is the live plan
while you use the wizard. Saving to Notion (explicit button or entering grocery
flow) writes a versioned row in the Weekly meal plans database *and* mirrors
the same recipe list to ``week_plan.json``.

**CLI** (``plan-recipes``, ``create-grocery-list``, ``dev validate-pipeline``):
reads **only** ``week_plan.json`` (or legacy ``.grocery_wizard/week_plan.json``)
unless you pass recipe names on the command line. It does not auto-load Notion
saved plans; pick a saved plan in the UI or run ``plan-recipes`` to refresh the
local file first.

**Notion saved weekly plans:** durable, versioned history keyed by week start.
The UI **Saved plan** mode loads a chosen plan into session state; that load
does not replace ``week_plan.json`` until you save or start grocery flow.

**``week_plan.json`` role:** shared local snapshot for CLI grocery runs,
``suggest_meals`` diversity hints (``load_recent_plan_names``), and a mirror
after UI commits to Notion. Treat it as the CLI's authoritative current plan,
not as the only copy of saved history (Notion holds that).
"""

from __future__ import annotations

__all__ = [
    "LoadedWeekPlan",
    "load_current_week_plan_from_file",
    "load_week_plan_names",
]

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from src.grocery_wizard.config import LEGACY_WEEK_PLAN_PATH, WEEK_PLAN_PATH


@dataclass(frozen=True)
class LoadedWeekPlan:
    """Recipe names plus a short label for logs and pipeline reports."""

    recipe_names: tuple[str, ...]
    source_label: str


def _read_week_plan_payload(resolved: Path) -> list[str]:
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: could not read week plan ({resolved}): {exc}", file=sys.stderr)
        return []
    if isinstance(data, dict):
        recipes = data.get("recipes", [])
        if isinstance(recipes, list):
            return [str(name).strip() for name in recipes if str(name).strip()]
    if isinstance(data, list):
        return [str(name).strip() for name in data if str(name).strip()]
    return []


def load_week_plan_names(path: Path = WEEK_PLAN_PATH) -> list[str]:
    """Return recipe names from the local week plan file (with legacy path fallback)."""
    resolved = path
    if not resolved.exists():
        if path == WEEK_PLAN_PATH and LEGACY_WEEK_PLAN_PATH.exists():
            resolved = LEGACY_WEEK_PLAN_PATH
        else:
            return []
    return _read_week_plan_payload(resolved)


def load_current_week_plan_from_file(
    path: Path = WEEK_PLAN_PATH,
) -> LoadedWeekPlan | None:
    """Load the CLI-facing current plan from disk, or ``None`` if missing/empty."""
    resolved = path
    if not resolved.exists() and path == WEEK_PLAN_PATH and LEGACY_WEEK_PLAN_PATH.exists():
        resolved = LEGACY_WEEK_PLAN_PATH
    names = load_week_plan_names(path)
    if not names:
        return None
    return LoadedWeekPlan(tuple(names), f"week plan ({resolved})")
