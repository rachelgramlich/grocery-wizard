"""AppTest smoke (#386): loading UX on weekly plan meal-count → meal builder."""

from __future__ import annotations

import pytest
from ui_source import APP_PATH, apptest_continue_to_meal_builder

from tests.notion_test_env import live_notion_smoke_enabled

pytestmark = pytest.mark.skipif(
    not live_notion_smoke_enabled(),
    reason="Live Notion credentials required for AppTest smoke",
)


def _visible_text(at) -> str:
    chunks: list[str] = []
    for block in (*at.markdown, *at.caption, *at.text):
        value = getattr(block, "value", None) or ""
        chunks.append(str(value))
    for status in getattr(at, "status", []) or []:
        label = getattr(status, "label", None) or ""
        chunks.append(str(label))
    return "\n".join(chunks)


def test_get_started_shows_no_notion_recipe_loading() -> None:
    """Get started must not show Notion recipe loading (quiet warm happens later)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)

    assert not at.exception, f"App exception: {at.exception}"
    text = _visible_text(at)
    assert "Loading recipes from Notion" not in text
    assert "Preparing your meal builder" not in text
    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Get started Continue missing"


def test_meal_count_continue_reaches_build_meals_without_notion_loading_copy() -> None:
    """After meal-count Continue, meal builder opens (Build my plan), no Notion load copy."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run(timeout=120)

    continue_buttons = [b for b in at.button if b.label == "Continue"]
    assert continue_buttons, "Get started Continue missing"
    continue_buttons[0].click().run(timeout=120)

    text = _visible_text(at)
    assert "Loading recipes from Notion" not in text

    apptest_continue_to_meal_builder(at, timeout=120)

    assert not at.exception, f"App exception: {at.exception}"
    build_buttons = [b for b in at.button if b.label == "Build my plan"]
    assert build_buttons, "Build my plan missing after meal-count Continue"
    text = _visible_text(at)
    assert "Loading recipes from Notion" not in text
