"""Repository and package path anchors (no I/O)."""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "BUNDLED_NLTK_DATA_DIR",
    "GOLDEN_GROCERY_WEEKS_DIR",
    "PACKAGE_ROOT",
    "RECIPES_DATA_DIR",
    "REPO_ROOT",
    "UI_APP_PATH",
    "UI_STATIC_DIR",
]

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
UI_APP_PATH = PACKAGE_ROOT / "ui" / "app.py"
UI_STATIC_DIR = PACKAGE_ROOT / "ui" / "static"
RECIPES_DATA_DIR = PACKAGE_ROOT / "recipes" / "data"
GOLDEN_GROCERY_WEEKS_DIR = REPO_ROOT / "tests" / "fixtures" / "golden_grocery_weeks"
BUNDLED_NLTK_DATA_DIR = REPO_ROOT / "resources" / "nltk_data"
