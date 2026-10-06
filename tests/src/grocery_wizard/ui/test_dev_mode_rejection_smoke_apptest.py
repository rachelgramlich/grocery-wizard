"""Live Notion AppTest: dev-mode Quick swap must not bump Rejection count (#317)."""

from __future__ import annotations

import pytest
from ui_source import APP_PATH

from src.grocery_wizard.integrations.notion import recipe_lookup_key
from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
    rejection_count_column_name,
    suggestion_rejection_count,
)
from src.grocery_wizard.ui.db_access import get_db
from tests.notion_test_env import live_notion_smoke_enabled

pytestmark = pytest.mark.skipif(
    not live_notion_smoke_enabled(),
    reason="Live Notion credentials required (NOTION_API_KEY not set on this agent)",
)


def _enter_dev_mode(at) -> None:
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan Continue missing"
    continue_buttons[0].click().run(timeout=120)

    change = [b for b in at.button if b.label == "Change how I started"]
    assert change, "Change how I started missing"
    change[0].click().run(timeout=120)

    session_radio = [r for r in at.radio if r.label == "Weekly plan session"]
    assert session_radio, "Weekly plan session radio missing"
    dev_opt = next(o for o in session_radio[0].options if "Dev mode" in o)
    session_radio[0].set_value(dev_opt).run(timeout=120)


def _rejection_count_for_recipe_name(recipe_name: str) -> int:
    db = get_db()
    column = rejection_count_column_name(db)
    if column is None:
        pytest.skip("Rejection count column not configured in Notion schema")
    rows = db.query_recipes()
    by_key = {recipe_lookup_key(r.name): r for r in rows}
    recipe = by_key.get(recipe_lookup_key(recipe_name))
    if recipe is None:
        pytest.skip(f"Recipe not found in Notion: {recipe_name!r}")
    return suggestion_rejection_count(recipe, rejections_column=column)


def test_dev_mode_quick_swap_does_not_increment_rejection_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Browser-equivalent smoke via AppTest + live Notion read before/after swap."""
    monkeypatch.setenv("GROCERY_WIZARD_DEV_UI", "1")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)
    _enter_dev_mode(at)

    auto_jump = [b for b in at.button if b.label == "Meals filled: auto"]
    assert auto_jump, "Dev jump Meals filled: auto missing"
    auto_jump[0].click().run(timeout=120)

    plan_text = str(at.session_state["plan_meals_text"]).strip()
    assert plan_text, "Dev jump should populate plan_meals_text"
    swapped_away = plan_text.splitlines()[0].strip()

    swap_buttons = [b for b in at.button if b.label == "Quick swap"]
    assert swap_buttons, "Quick swap button missing after dev jump"

    before = _rejection_count_for_recipe_name(swapped_away)
    swap_buttons[0].click().run(timeout=120)
    assert not at.exception, f"App exception after Quick swap: {at.exception}"

    after = _rejection_count_for_recipe_name(swapped_away)
    assert after == before, (
        f"Dev mode Quick swap changed Rejection count for {swapped_away!r}: {before} → {after}"
    )
