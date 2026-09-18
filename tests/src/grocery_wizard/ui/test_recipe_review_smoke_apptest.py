"""AppTest smoke: per-recipe review form submit builds the final grocery list (#237)."""

from __future__ import annotations

import os

import pytest
from ui_source import APP_PATH

_PYTEST_NOTION_API_KEY = "pytest-notion-integration-test-key"

pytestmark = pytest.mark.skipif(
    not os.environ.get("NOTION_API_KEY")
    or os.environ.get("NOTION_API_KEY") == _PYTEST_NOTION_API_KEY,
    reason="Real Notion credentials required for live AppTest smoke",
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


def test_per_recipe_review_form_submit_reaches_final_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live Notion: dev jump → review form → Build final list → grocery result UI."""
    monkeypatch.setenv("GROCERY_WIZARD_DEV_UI", "1")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)
    _enter_dev_mode(at)

    review_jump = [b for b in at.button if b.label == "Per-recipe review"]
    assert review_jump, "Dev jump Per-recipe review button missing"
    review_jump[0].click().run(timeout=120)

    assert at.text_area, "Expected per-recipe ingredient text areas"
    edited = f"{(at.text_area[0].value or '').rstrip()}\n2 cups UNIQUE237SMOKE".strip()
    at.text_area[0].set_value(edited)

    submit = [b for b in at.button if b.label == "Build final list"]
    assert submit, "Build final list form submit missing"
    submit[0].click().run(timeout=120)

    assert not at.exception, f"App exception: {at.exception}"
    assert "grocery_result" in at.session_state
    assert "grocery_per_recipe_review" not in at.session_state
    grocery_areas = [t for t in at.text_area if t.key == "grocery_final_list"]
    assert grocery_areas, "Final grocery list text area missing"
