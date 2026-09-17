"""Tests for ingredients sync merge logic and removal directives."""

from __future__ import annotations

import pytest

from src.grocery_wizard.ingredients.sync import (
    apply_removals,
    format_ingredients_for_review,
    is_directive,
    is_removal_directive,
    merge_ingredients,
    parse_ingredients_text,
    parse_removal_target,
    prepare_ingredients_for_notion,
    split_ingredients_text,
)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("remove: salt", True),
        ("remove salt", True),
        ("REMOVE olive oil", True),
        ("- salt", True),
        ("2 cups flour", False),
        ("kosher salt", False),
    ],
)
def test_is_removal_directive(line: str, expected: bool) -> None:
    assert is_removal_directive(line) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("remove: salt", "salt"),
        ("remove salt", "salt"),
        ("REMOVE olive oil", "olive oil"),
        ("- garlic", "garlic"),
    ],
)
def test_parse_removal_target(line: str, expected: str) -> None:
    assert parse_removal_target(line) == expected


def test_parse_ingredients_text_merges_wrapped_nyt_lines() -> None:
    text = "2 medium leeks, light green\nwhite parts only, halved\nSalt\nand pepper, to taste"
    ingredients, _ = parse_ingredients_text(text)
    assert ingredients == [
        "2 medium leeks, light green white parts only, halved",
        "Salt and pepper, to taste",
    ]


def test_format_ingredients_for_review_merges_wrapped_lines() -> None:
    stored = "Salt\nand pepper, to taste\n2 medium leeks, light green\nwhite parts only"
    display = format_ingredients_for_review(stored)
    lines = display.splitlines()
    assert lines == [
        "Salt and pepper, to taste",
        "2 leeks, light green white parts only",
    ]


def test_parse_ingredients_text_splits_ingredients_and_removals() -> None:
    text = "2 tbsp olive oil\n1 lb chicken\nremove: salt\n- garlic\n# pantry note\nfresh basil"
    ingredients, removals = parse_ingredients_text(text)
    assert ingredients == ["2 tbsp olive oil", "1 lb chicken", "fresh basil"]
    assert removals == ["salt", "garlic"]


def test_is_directive() -> None:
    assert is_directive("remove: pepper")
    assert is_directive("# comment")
    assert not is_directive("2 cups rice")


def test_format_ingredients_for_review_expands_storage_encodings() -> None:
    stored = "olive oil\n1/2 onions\nclove:5 garlic\nzest lemons\n2 cans white beans\nremove: salt"
    display = format_ingredients_for_review(stored)
    lines = display.splitlines()
    assert "olive oil" in lines
    assert "1/2 onions" in lines
    assert "5 cloves garlic" in lines
    assert "clove:5" not in display
    assert "zest of 1 lemon" in lines
    assert "2 cans white beans" in lines
    assert "remove: salt" in lines


def test_prepare_ingredients_for_notion_strips_trailing_prep() -> None:
    text = "2 small yellow onions, sliced 1/4 inch thick lengthwise"
    prepared = prepare_ingredients_for_notion(text)
    assert prepared == "2 small yellow onions"


def test_prepare_ingredients_for_notion_splits_and_drops_junk() -> None:
    text = "2 sweet potatoes and 1 red onion\nsliced into half-moons\nremove: garlic\n"
    prepared = prepare_ingredients_for_notion(text)
    lines = [line for line in prepared.splitlines() if line.strip()]
    assert any("sweet potatoes" in line for line in lines)
    assert any("red onion" in line for line in lines)
    assert "remove: garlic" in lines
    assert not any("half-moons" in line for line in lines)


def test_prepare_ingredients_for_notion_drops_instructions_and_metadata() -> None:
    text = "Recipe serves 2\n2 tablespoons olive oil\n1.\tHeat the olive oil\nstir to combine."
    prepared = prepare_ingredients_for_notion(text)
    lines = prepared.splitlines()
    assert lines == ["olive oil"]


def test_prepare_ingredients_for_notion_repairs_mangled_lines() -> None:
    text = (
        "2 pounds Idaho Burbank Russets2 Tablespoons scallions, finely mincedSalt\n"
        "fresh black pepper1/4 cup chicken stock"
    )
    prepared = prepare_ingredients_for_notion(text)
    lines = prepared.splitlines()
    assert "2 lb Idaho Burbank Russets" in lines
    assert any("scallions" in line for line in lines)
    assert "Salt" in lines
    assert any("black pepper" in line for line in lines)
    assert any("chicken stock" in line for line in lines)


def test_merge_keeps_notion_additions_not_in_scrape() -> None:
    existing = "2 tbsp olive oil\n1 lb chicken\nfresh basil"
    scraped = "2 tbsp olive oil\n3 cloves garlic\n1 lb chicken breast"
    merged = merge_ingredients(existing, scraped)
    lines = [line for line in merged.splitlines() if line.strip()]
    assert "fresh basil" in lines
    assert any("garlic" in line for line in lines)
    assert any("chicken" in line for line in lines)


def test_merge_dedupes_by_normalized_name() -> None:
    existing = "2 tablespoons olive oil"
    scraped = "3 tbsp olive oil, plus more for drizzling"
    merged = merge_ingredients(existing, scraped)
    olive_lines = [line for line in merged.splitlines() if "olive" in line.lower()]
    assert len(olive_lines) == 1


def test_merge_applies_removal_directives() -> None:
    existing = "2 tbsp olive oil\nkosher salt\nremove: salt\n1 lb chicken"
    scraped = "2 tbsp olive oil\nkosher salt\n3 cloves garlic\n1 lb chicken"
    merged = merge_ingredients(existing, scraped)
    lines = [line.lower() for line in merged.splitlines() if line.strip()]
    assert not any("salt" in line for line in lines)
    assert any("garlic" in line for line in lines)


def test_apply_removals_substring_match() -> None:
    lines = ["kosher salt", "2 tbsp olive oil", "1 lb chicken"]
    result = apply_removals(lines, ["salt"])
    assert result == ["2 tbsp olive oil", "1 lb chicken"]


def test_split_ingredients_text_preserves_directives() -> None:
    text = "Naan bread and rice\nremove: salt\n# pantry note"
    result = split_ingredients_text(text)
    lines = result.splitlines()
    assert lines[0] == "Naan bread"
    assert lines[1] == "rice"
    assert lines[2] == "remove: salt"
    assert lines[3] == "# pantry note"


def test_notion_fixture_prepare(notion_case: dict) -> None:
    """Notion-derived lines: prepare_ingredients_for_notion matches fixture expectations."""
    raw = notion_case["raw_line"]
    expected = notion_case["expect_after_prepare"]
    result = prepare_ingredients_for_notion(raw)

    if expected is None:
        assert result == raw.strip()
    else:
        assert result == expected


def test_notion_fixture_preserves_removal_directives(notion_removal_case: dict) -> None:
    prepared = prepare_ingredients_for_notion(notion_removal_case["raw_line"])
    assert "remove: garlic" in prepared.splitlines()


def test_backfill_preserves_manual_substitution_notes() -> None:
    """Reformat must not drop manual substitution / note lines from real recipes."""
    text = (
        "2 cans (15 oz each) black beans, rinsed\n"
        "1 chicken bouillon cube (or substitute 2 cups chicken broth for the water bouillon)\n"
        "5 oz fresh spinach (or frozen, see notes below)\n"
        "Salt, to taste\n"
        "1 tablespoon plain Greek yogurt (optional)\n"
        "remove: salt\n"
    )
    prepared = prepare_ingredients_for_notion(text)
    lines = prepared.splitlines()
    assert any("bouillon" in line for line in lines)
    assert any("see notes" in line for line in lines)
    assert any("to taste" in line.lower() for line in lines)
    assert any(line.startswith("remove:") for line in lines)
