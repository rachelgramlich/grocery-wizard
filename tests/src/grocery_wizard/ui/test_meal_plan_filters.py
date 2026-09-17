"""Tests for meal-plan filter helpers."""

from __future__ import annotations

from src.grocery_wizard.ui.meal_plan_filters import scoped_ingredient_multiselect_options


def test_scoped_ingredient_options_keeps_selected() -> None:
    all_options = ["apple", "banana", "carrot", "date"]
    selected = ["banana"]
    options = scoped_ingredient_multiselect_options(all_options, selected, "z", max_matches=10)
    assert options == ["banana"]


def test_scoped_ingredient_options_search_caps_matches() -> None:
    all_options = [f"item-{index}" for index in range(300)]
    options = scoped_ingredient_multiselect_options(all_options, [], "item", max_matches=20)
    assert len(options) == 20


def test_scoped_ingredient_options_search_is_case_insensitive() -> None:
    all_options = ["Chicken breast", "chickpeas", "rice"]
    options = scoped_ingredient_multiselect_options(all_options, [], "CHICK")
    assert options == ["Chicken breast", "chickpeas"]
