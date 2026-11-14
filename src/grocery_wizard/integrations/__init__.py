"""External service integrations (Notion, NYT Cooking, …)."""

from src.grocery_wizard.integrations.notion import NotionRecipesDB, Recipe

__all__ = ["NotionRecipesDB", "Recipe"]
