"""Populate a compatibility module namespace from a target submodule."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def reexport_module(target: ModuleType, namespace: dict[str, object]) -> None:
    for name in dir(target):
        if name.startswith("__") and name != "__all__":
            continue
        namespace[name] = getattr(target, name)
    if hasattr(target, "__all__"):
        namespace["__all__"] = list(target.__all__)
