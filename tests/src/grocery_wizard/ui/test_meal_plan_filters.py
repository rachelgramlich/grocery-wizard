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


def test_scoped_ingredient_options_without_query_includes_every_option() -> None:
    """#439: the multiselect's own search must find "pasta" even in a long ingredient list."""
    all_options = [f"ingredient-{index:04d}" for index in range(400)] + ["pasta"]
    options = scoped_ingredient_multiselect_options(all_options, [], "")
    assert "pasta" in options
    assert len(options) == len(all_options)


def test_scoped_ingredient_options_without_query_does_not_duplicate_selected() -> None:
    all_options = ["apple", "pasta", "rice"]
    options = scoped_ingredient_multiselect_options(all_options, ["pasta"], "  ")
    assert options == ["apple", "pasta", "rice"]


def test_scoped_ingredient_options_query_finds_pasta_past_the_cap() -> None:
    all_options = [f"pasta-{index:04d}" for index in range(300)] + ["pasta"]
    options = scoped_ingredient_multiselect_options(all_options, [], "pasta", max_matches=500)
    assert "pasta" in options
