"""Top-level Streamlit section labels."""

from __future__ import annotations

_TAB_WEEKLY = "Create weekly plan"
_TAB_ADD = "Add Recipe"
_TAB_PANTRY = "Pantry & recurring"
_TAB_MAINTENANCE = "Recipe maintenance"
_UI_TABS = (_TAB_WEEKLY, _TAB_ADD, _TAB_PANTRY, _TAB_MAINTENANCE)

# Stable Streamlit container keys (tab labels include spaces and punctuation).
_TAB_CONTAINER_KEYS: dict[str, str] = {
    _TAB_WEEKLY: "weekly",
    _TAB_ADD: "add",
    _TAB_PANTRY: "pantry",
    _TAB_MAINTENANCE: "maintenance",
}
