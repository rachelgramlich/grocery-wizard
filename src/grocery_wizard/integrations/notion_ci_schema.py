"""Compatibility shim — use ``integrations.notion.ci_schema``."""

from __future__ import annotations

from src.grocery_wizard.integrations import _reexport_shim
from src.grocery_wizard.integrations.notion import ci_schema as _target

_reexport_shim.reexport_module(_target, globals())
