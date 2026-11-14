"""Cold-start-safe Notion household database constructors.

Household DB classes live behind ``notion_household`` shims. These helpers keep
one lazy import site instead of duplicating it across shopping, UI cache, and perf audit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.grocery_wizard.integrations.notion import NotionRecipesDB
    from src.grocery_wizard.integrations.notion_household import (
        NotionPantryDB,
        NotionRecurringDB,
        NotionWeeklyPlansDB,
    )

__all__ = [
    "notion_pantry_db",
    "notion_recurring_db",
    "notion_weekly_plans_db",
]


def notion_pantry_db() -> NotionPantryDB:
    from src.grocery_wizard.integrations.notion_household import NotionPantryDB

    return NotionPantryDB()


def notion_recurring_db() -> NotionRecurringDB:
    from src.grocery_wizard.integrations.notion_household import NotionRecurringDB

    return NotionRecurringDB()


def notion_weekly_plans_db(
    *,
    recipes_db: NotionRecipesDB | None = None,
) -> NotionWeeklyPlansDB:
    from src.grocery_wizard.integrations.notion_household import NotionWeeklyPlansDB

    return NotionWeeklyPlansDB(recipes_db=recipes_db)
