"""Lazy entry points to the recipe stack from NYT sync (light ``nyt_cooking`` import)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


def add_prefetched_recipes(db: Any, recipes: Sequence[tuple[Any, ...]], **kwargs: Any) -> list[Any]:
    from src.grocery_wizard.recipes.add_recipe import add_prefetched_recipes as _impl

    return _impl(db, list(recipes), **kwargs)


def filter_columns_for_recipe_classify(filter_columns: list[Any]) -> list[Any]:
    from src.grocery_wizard.recipes.recipe_meal_plan_stats import (
        filter_columns_for_recipe_classify as _impl,
    )

    return _impl(filter_columns)


def classify_recipe(
    title: str, ingredients: list[str], filter_columns: list[Any], **kwargs: Any,
) -> Any:
    from src.grocery_wizard.recipes.classify import classify_recipe as _impl

    return _impl(title, ingredients, filter_columns, **kwargs)


def default_weeknight_column() -> str:
    from src.grocery_wizard.recipes.weeknight import DEFAULT_WEEKNIGHT_COLUMN

    return DEFAULT_WEEKNIGHT_COLUMN


def is_weeknight_friendly(
    title: str,
    *,
    meal: str | None,
    total_minutes: float | None = None,
) -> bool:
    from src.grocery_wizard.recipes.weeknight import is_weeknight_friendly as _impl

    return _impl(title, meal=meal, total_minutes=total_minutes)


def scrape_recipe_from_url(url: str) -> Any:
    from src.grocery_wizard.recipes.scraper import scrape_recipe as _impl

    return _impl(url)


def scrape_error_type() -> type[BaseException]:
    from src.grocery_wizard.recipes.scraper import ScrapeError

    return ScrapeError
