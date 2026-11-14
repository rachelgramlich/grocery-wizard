"""Repo and test tree paths — single owner for pytest path literals."""

from __future__ import annotations

from src.grocery_wizard.paths import PACKAGE_ROOT, REPO_ROOT

SRC_PACKAGE_ROOT = PACKAGE_ROOT
TESTS_DIR = REPO_ROOT / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"
UI_SRC_ROOT = SRC_PACKAGE_ROOT / "ui"
UI_TEST_HELPERS = TESTS_DIR / "src" / "grocery_wizard" / "ui"


def package_module_source(rel: str) -> str:
    """Read a module under ``src/grocery_wizard`` as UTF-8 text."""
    return (SRC_PACKAGE_ROOT / rel).read_text(encoding="utf-8")
