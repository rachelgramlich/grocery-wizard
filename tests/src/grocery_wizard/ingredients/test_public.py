"""Smoke tests for ingredients.public facade exports."""

from __future__ import annotations

from src.grocery_wizard.ingredients import public


def test_public_exports_are_callable() -> None:
    assert public.normalize_ingredient("2 cups flour") == "flour"
    assert public.name_from_stored_line("2 cups flour") == "flour"
    assert public.format_ingredient_for_storage("2 cups flour")


def test_storage_and_grocery_names_differ_for_checklist_lines() -> None:
    raw = "[x] 1 onion, diced"
    assert public.name_from_stored_line(raw) != public.normalize_ingredient(raw)
    assert public.normalize_ingredient(raw).startswith("[x]")
