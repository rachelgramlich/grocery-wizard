"""Notion integration subpackage (recipes, household DBs, tables, views)."""

from __future__ import annotations

from src.grocery_wizard.integrations import _reexport_shim
from src.grocery_wizard.integrations.notion import recipes as _recipes

_reexport_shim.reexport_module(_recipes, globals())
