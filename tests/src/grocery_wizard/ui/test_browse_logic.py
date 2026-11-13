"""Browse recipes filter and sort helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from src.grocery_wizard.integrations.notion import Recipe
from src.grocery_wizard.planning.meal_planner import MealPlanFilters
from src.grocery_wizard.ui.browse_logic import (
    BrowseAppliedFilters,
    browse_recipes_for_applied,
    render_browse_grid_html,
    sort_browse_recipes,
)


def _recipe(
    name: str,
    *,
    page_id: str,
    selection: int = 0,
    rejection: int = 0,
    edited: datetime | None = None,
    image: str | None = None,
) -> Recipe:
    return Recipe(
        page_id=page_id,
        name=name,
        link=None,
        ingredients=None,
        properties={
            "Selection count": selection,
            "Rejection count": rejection,
        },
        last_edited_time=edited,
        image_file_url=image,
    )


def test_sort_browse_recipes_orders_by_counts_then_edited() -> None:
    recipes = [
        _recipe(
            "B", page_id="b", selection=2, rejection=1, edited=datetime(2025, 1, 2, tzinfo=UTC)
        ),
        _recipe(
            "A", page_id="a", selection=1, rejection=0, edited=datetime(2025, 1, 3, tzinfo=UTC)
        ),
        _recipe(
            "C", page_id="c", selection=2, rejection=1, edited=datetime(2025, 1, 1, tzinfo=UTC)
        ),
    ]
    ordered = sort_browse_recipes(
        recipes,
        sort_seed=42,
        selection_column="Selection count",
        rejections_column="Rejection count",
    )
    names = [recipe.name for recipe in ordered]
    assert names == ["A", "C", "B"]


def test_has_image_filter_excludes_placeholders() -> None:
    from unittest.mock import MagicMock

    from src.grocery_wizard.integrations.notion import DatabaseSchema

    db = MagicMock()
    db.schema = DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column=None,
        filter_columns=[],
        checkbox_columns=[],
        all_columns={},
    )
    recipes = [
        _recipe("With photo", page_id="1", image="https://notion.so/file.jpg"),
        _recipe("No photo", page_id="2", image=None),
    ]
    applied = BrowseAppliedFilters(meal_filters=MealPlanFilters(), has_image=True)
    result = browse_recipes_for_applied(
        recipes,
        db,
        applied,
        ingredient_index=None,
        sort_seed=1,
    )
    assert [r.name for r in result] == ["With photo"]


def test_render_browse_grid_html_includes_placeholder_and_title() -> None:
    html = render_browse_grid_html(
        [_recipe("Soup", page_id="x", image=None)],
        limit=24,
    )
    assert "gw-browse-grid" in html
    assert "No photo" in html
    assert "Soup" in html
    assert "pointer-events" not in html
