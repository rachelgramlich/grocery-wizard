"""Repo and test tree paths — single owner for pytest path literals."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PACKAGE_ROOT = REPO_ROOT / "src" / "grocery_wizard"
TESTS_DIR = REPO_ROOT / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"
UI_SRC_ROOT = SRC_PACKAGE_ROOT / "ui"
UI_TEST_HELPERS = TESTS_DIR / "src" / "grocery_wizard" / "ui"
