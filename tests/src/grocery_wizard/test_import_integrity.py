"""Import safety net: names imported inside functions and cold-process startup.

A name imported at the top of a module fails the moment pytest imports it. A name imported
*inside a function* only fails when that line runs, which is how a missing helper reached
Streamlit Cloud with a green CI. These tests check every internal import without running it.
"""

from __future__ import annotations

import ast
import importlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.repo_paths import REPO_ROOT

PACKAGE_ROOT = REPO_ROOT / "src" / "grocery_wizard"
INTERNAL_PREFIX = "src.grocery_wizard"


@dataclass(frozen=True)
class InternalImport:
    source_file: Path
    line: int
    module: str
    name: str

    def describe(self) -> str:
        relative = self.source_file.relative_to(REPO_ROOT)
        return f"{relative}:{self.line}: from {self.module} import {self.name}"


def _module_name_for(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_from_module(node: ast.ImportFrom, source_file: Path) -> str | None:
    if node.level == 0:
        return node.module
    package_parts = _module_name_for(source_file).split(".")
    if source_file.name != "__init__.py":
        package_parts.pop()
    keep = len(package_parts) - (node.level - 1)
    if keep <= 0:
        return None
    base = ".".join(package_parts[:keep])
    return f"{base}.{node.module}" if node.module else base


def _collect_internal_imports() -> list[InternalImport]:
    found: list[InternalImport] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_from_module(node, path)
            if module is None or not module.startswith(INTERNAL_PREFIX):
                continue
            found.extend(
                InternalImport(path, node.lineno, module, alias.name)
                for alias in node.names
                if alias.name != "*"
            )
    return found


def _importable_modules() -> list[str]:
    names = {_module_name_for(path) for path in PACKAGE_ROOT.rglob("*.py")}
    return sorted(name for name in names if not name.endswith("__main__"))


def test_collector_sees_function_level_imports() -> None:
    """Guard the guard: lazy imports inside functions must be in the scanned set."""
    imports = _collect_internal_imports()
    assert any(
        i.name == "clear_notion_database_metadata_cache"
        and i.source_file.name == "app.py"
        and i.module.endswith("notion_table")
        for i in imports
    )
    assert len(imports) > 100


def test_every_internal_from_import_names_something_that_exists() -> None:
    missing: list[str] = []
    for item in _collect_internal_imports():
        try:
            module = importlib.import_module(item.module)
        except Exception as exc:
            missing.append(f"{item.describe()} (module failed to import: {exc!r})")
            continue
        if hasattr(module, item.name):
            continue
        try:
            importlib.import_module(f"{item.module}.{item.name}")
        except ImportError:
            missing.append(item.describe())
    assert not missing, "Imports that would raise ImportError at runtime:\n" + "\n".join(missing)


def test_listed_modules_cover_the_whole_package() -> None:
    modules = _importable_modules()
    assert f"{INTERNAL_PREFIX}.ui.app" in modules
    assert f"{INTERNAL_PREFIX}.integrations.notion_table" in modules
    assert len(modules) > 40


def test_every_module_imports_in_a_fresh_interpreter() -> None:
    """Pytest fixtures patch modules in-process; a cold interpreter shows real import order."""
    script = "\n".join(
        [
            "import importlib, sys",
            "failures = []",
            f"for name in {_importable_modules()!r}:",
            "    try:",
            "        importlib.import_module(name)",
            "    except Exception as exc:",
            "        failures.append(f'{name}: {exc!r}')",
            "print('\\n'.join(failures))",
            "sys.exit(1 if failures else 0)",
        ]
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "NOTION_API_KEY": os.environ.get("NOTION_API_KEY", "test-placeholder"),
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, f"Cold import failures:\n{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize("module", [f"{INTERNAL_PREFIX}.ui.app"])
def test_streamlit_entry_module_exposes_main(module: str) -> None:
    assert callable(importlib.import_module(module).main)
