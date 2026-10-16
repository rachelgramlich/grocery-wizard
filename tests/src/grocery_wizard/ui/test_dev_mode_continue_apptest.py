"""AppTest: dev mode Continue to grocery unlocks grocery step (#344)."""

from __future__ import annotations

import pytest
from ui_source import APP_PATH, apptest_continue_to_meal_builder, apptest_rail_get_started

from src.grocery_wizard.ui.dev_jumps import DEV_JUMP_BUTTON_LABEL_MEALS_FILLED_AUTO
from tests.notion_test_env import live_notion_smoke_enabled

pytestmark = pytest.mark.skipif(
    not live_notion_smoke_enabled(),
    reason="Live Notion credentials required for AppTest smoke",
)


def _enter_dev_mode(at) -> None:
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Weekly plan Continue missing"
    continue_buttons[0].click().run(timeout=120)
    apptest_rail_get_started(at, timeout=120)

    change = [b for b in at.button if b.label == "Change how I started"]
    assert change, "Change how I started missing"
    change[0].click().run(timeout=120)

    session_radio = [r for r in at.radio if r.label == "Weekly plan session"]
    assert session_radio, "Weekly plan session radio missing"
    dev_opt = next(o for o in session_radio[0].options if "Dev mode" in o)
    session_radio[0].set_value(dev_opt).run(timeout=120)
    apptest_continue_to_meal_builder(at, timeout=120)


def test_dev_mode_continue_to_grocery_unlocks_grocery_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROCERY_WIZARD_DEV_UI", "1")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)
    _enter_dev_mode(at)

    auto_jump = [b for b in at.button if b.label == DEV_JUMP_BUTTON_LABEL_MEALS_FILLED_AUTO]
    assert auto_jump, f"Dev jump {DEV_JUMP_BUTTON_LABEL_MEALS_FILLED_AUTO!r} missing"
    auto_jump[0].click().run(timeout=120)

    continue_grocery = [b for b in at.button if b.label == "Continue to grocery list"]
    assert continue_grocery, "Dev continue button missing in 1c"
    assert not [b for b in at.button if b.label == "Save plan to Notion"], (
        "Save plan to Notion should not appear in dev mode"
    )

    continue_grocery[0].click().run(timeout=120)
    assert not at.exception, f"App exception after continue: {at.exception}"

    create_list = [b for b in at.button if b.label == "Create grocery list"]
    assert create_list, "Grocery step should unlock with Create grocery list button"
