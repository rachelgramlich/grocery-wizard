"""Source checks: meal-plan status controls in per-recipe review."""

from __future__ import annotations

from ui_source import ui_source


def test_recipe_review_exposes_meal_plan_status_controls() -> None:
    source = ui_source()
    assert "render_meal_plan_status_for_recipe" in source
    assert 'scope="review"' in source
    assert "Apply meal plan status" in source
