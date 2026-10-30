"""Tests for pantry file parsing and display."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.grocery_wizard.shopping.pantry import (
    _matches_pantry_search,
    append_pantry_item,
    format_pantry_display,
    is_pantry_item,
    load_pantry,
    parse_pantry_file,
    remove_pantry_item_by_name,
    write_pantry_file,
)


def test_load_pantry_ignores_comments_and_headers(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text(
        "# header\nsalt\n# --- section ---\npepper\n",
        encoding="utf-8",
    )
    assert load_pantry(path) == {"salt", "pepper"}


def test_parse_pantry_file_groups_by_section_headers(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text(
        "# --- Spices ---\ncumin\npaprika\n# --- Oils ---\nolive oil\n",
        encoding="utf-8",
    )
    lines, sections = parse_pantry_file(path)
    assert len(sections) == 2
    assert sections[0].header == "# --- Spices ---"
    assert [item for _idx, item in sections[0].items] == ["cumin", "paprika"]
    assert sections[1].header == "# --- Oils ---"
    assert [item for _idx, item in sections[1].items] == ["olive oil"]
    assert len(lines) == 5


def test_format_pantry_display_numbered(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text("# --- Spices ---\ncumin\n", encoding="utf-8")
    _lines, sections = parse_pantry_file(path)
    display = format_pantry_display(sections)
    assert "# --- Spices ---" in display
    assert "  1. cumin" in display


def test_write_pantry_file_adds_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    write_pantry_file(path, ["salt", "pepper"])
    assert path.read_text(encoding="utf-8") == "salt\npepper\n"


@pytest.mark.parametrize(
    ("ingredient", "expected"),
    [
        ("kosher salt", True),
        ("olive oil", True),
        ("beef", False),
        ("ground beef", False),
        ("white beans", False),
        ("rice", True),
        ("brown rice", True),
    ],
)
def test_is_pantry_item_phrase_matching(ingredient: str, expected: bool) -> None:
    pantry = {"salt", "olive oil", "beef stock", "rice", "white wine vinegar"}
    assert is_pantry_item(ingredient, pantry) is expected


@pytest.mark.parametrize(
    ("ingredient", "pantry_items", "expected"),
    [
        # single-token "oil" matches last word of any oil phrase
        ("oil", {"olive oil", "vegetable oil"}, True),
        # single-token "oil" does NOT match unrelated pantry entries
        ("oil", {"salt"}, False),
        # multi-word ingredient must not match via the last-word shortcut
        ("unsalted butter", {"salt"}, False),
    ],
)
def test_is_pantry_item_single_token_last_word_rule(
    ingredient: str, pantry_items: set[str], expected: bool
) -> None:
    assert is_pantry_item(ingredient, pantry_items) is expected


@pytest.mark.parametrize(
    ("search", "item", "expected"),
    [
        ("salt", "salt", True),
        ("beef stock", "beef stock", True),
        ("beef", "beef stock", True),
        ("stock", "beef stock", True),
        ("low sodium beef stock", "beef stock", True),
        ("ice", "rice", False),
        ("vinegar", "white wine vinegar", True),
        ("wine", "white wine vinegar", True),
    ],
)
def test_matches_pantry_search(search: str, item: str, expected: bool) -> None:
    assert _matches_pantry_search(search, item) is expected


def test_hyphenated_red_pepper_flakes_matches_pantry_entry() -> None:
    pantry = {"red pepper flakes", "pepper"}
    assert is_pantry_item("red-pepper flakes", pantry)
    assert is_pantry_item("red pepper flakes", pantry)


def test_fresh_red_pepper_not_matched_by_generic_pepper_pantry() -> None:
    pantry = {"pepper", "red pepper flakes"}
    assert not is_pantry_item("red pepper", pantry)
    assert is_pantry_item("red pepper flakes", pantry)


def test_fresh_red_bell_pepper_not_matched_by_generic_pepper_pantry() -> None:
    pantry = {"pepper"}
    assert not is_pantry_item("red bell pepper", pantry)
    assert not is_pantry_item("2 red bell peppers", pantry)
    assert is_pantry_item("red bell pepper", {"red bell pepper"})


@pytest.mark.parametrize(
    "variety",
    [
        "white",
        "black",
        "pinto",
        "kidney",
        "butter",
        "cannellini",
        "navy",
    ],
)
def test_named_bean_varieties_not_matched_by_generic_or_modifier_pantry(
    variety: str,
) -> None:
    ingredient = f"{variety} beans"
    assert not is_pantry_item(ingredient, {"beans"})
    assert not is_pantry_item(ingredient, {variety})
    assert is_pantry_item(ingredient, {ingredient})
    assert is_pantry_item("beans", {"beans"})


def test_peanut_butter_not_matched_by_dairy_butter_pantry() -> None:
    assert not is_pantry_item("peanut butter", {"butter"})
    assert is_pantry_item("peanut butter", {"peanut butter"})


def test_butter_lettuce_not_matched_by_dairy_butter_pantry() -> None:
    assert not is_pantry_item("butter lettuce", {"butter"})
    assert is_pantry_item("butter lettuce", {"butter lettuce"})
    assert is_pantry_item("butter lettuce", {"lettuce"})


def test_cauliflower_rice_not_matched_by_rice_pantry() -> None:
    pantry = {"rice"}
    assert not is_pantry_item("cauliflower rice", pantry)
    assert not is_pantry_item("riced cauliflower", pantry)
    assert is_pantry_item("brown rice", pantry)
    assert is_pantry_item("rice", pantry)


def test_frozen_pantry_product_does_not_exclude_plain_last_word_ingredient() -> None:
    pantry = {"frozen edamame", "canned tomatoes"}
    assert not is_pantry_item("edamame", pantry)
    assert not is_pantry_item("tomatoes", pantry)
    assert is_pantry_item("frozen edamame", pantry)
    assert is_pantry_item("canned tomatoes", pantry)


def test_edamame_comma_shelled_matches_pantry_edamame() -> None:
    from src.grocery_wizard.ingredients.normalize import normalize_ingredient

    pantry = {"edamame"}
    assert normalize_ingredient("edamame, shelled") == "edamame"
    assert is_pantry_item(normalize_ingredient("edamame, shelled"), pantry)
    assert is_pantry_item("shelled edamame", pantry)


def test_append_and_remove_pantry_item(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text("# --- Spices ---\nsalt\n", encoding="utf-8")
    assert append_pantry_item("cumin", path=path)
    assert "cumin" in load_pantry(path)
    assert append_pantry_item("cumin", path=path) is False
    assert remove_pantry_item_by_name("salt", path=path)
    assert "salt" not in load_pantry(path)


@pytest.mark.parametrize(
    "ingredient",
    [
        "fresno pepper",
        "fresno peppers",
        "jalapeno pepper",
        "green pepper",
        "red pepper",
        "red bell pepper",
        "2 red bell peppers",
        "yellow pepper",
        "serrano pepper",
        "white pepper",
        "pepper jack cheese",
        "red-pepper flakes",
    ],
)
@pytest.mark.parametrize("pantry_entry", ["pepper", "black pepper", "ground black pepper"])
def test_only_table_pepper_is_matched_by_generic_pepper_pantry(
    ingredient: str, pantry_entry: str
) -> None:
    assert not is_pantry_item(ingredient, {pantry_entry})


@pytest.mark.parametrize(
    "ingredient",
    ["pepper", "black pepper", "ground black pepper", "salt and pepper"],
)
def test_table_pepper_is_matched_by_generic_pepper_pantry(ingredient: str) -> None:
    assert is_pantry_item(ingredient, {"pepper"})


def test_specific_pepper_pantry_entry_still_matches_itself() -> None:
    assert is_pantry_item("fresno pepper", {"fresno pepper"})


def test_remove_pepper_does_not_remove_fresno_pepper(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text("salt\nfresno pepper\njalapeno pepper\n", encoding="utf-8")
    assert not remove_pantry_item_by_name("pepper", path)
    assert load_pantry(path) == {"salt", "fresno pepper", "jalapeno pepper"}


def test_remove_pepper_removes_black_pepper(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text("fresno pepper\nblack pepper\n", encoding="utf-8")
    assert remove_pantry_item_by_name("pepper", path)
    assert load_pantry(path) == {"fresno pepper"}


def test_remove_fresno_pepper_does_not_remove_plain_pepper(tmp_path: Path) -> None:
    path = tmp_path / "pantry.txt"
    path.write_text("pepper\n", encoding="utf-8")
    assert not remove_pantry_item_by_name("fresno pepper", path)


@pytest.mark.parametrize(
    ("ingredient", "pantry_entry"),
    [
        ("avocado oil", "avocado oil"),
        ("avocado oil spray", "avocado oil"),
        ("old bay", "old bay"),
        ("old bay seasoning", "old bay"),
        ("chili powder", "chili powder"),
        ("ancho chili powder", "chili powder"),
        ("chile powder", "chili powder"),
        ("chilli powder", "chili powder"),
        ("chili powder", "chile powder"),
        ("kashmiri red chile powder", "chili powder"),
    ],
)
def test_multi_word_pantry_staples_match_recipe_names(ingredient: str, pantry_entry: str) -> None:
    assert is_pantry_item(ingredient, {pantry_entry})


@pytest.mark.parametrize(
    ("ingredient", "pantry_entry"),
    [
        ("olive oil", "avocado oil"),
        ("oil", "avocado oil spray"),
        ("avocados", "avocado oil"),
        ("bay leaves", "old bay"),
        ("chili sauce", "chili powder"),
        ("chile crisp", "chili powder"),
        ("chile oil", "chili powder"),
        ("green chile pepper", "chili powder"),
        ("fresno pepper", "pepper"),
    ],
)
def test_multi_word_pantry_staples_do_not_match_other_products(
    ingredient: str, pantry_entry: str
) -> None:
    assert not is_pantry_item(ingredient, {pantry_entry})
