"""Repository and package path anchors (no I/O)."""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
UI_APP_PATH = PACKAGE_ROOT / "ui" / "app.py"
GOLDEN_GROCERY_WEEKS_DIR = REPO_ROOT / "tests" / "fixtures" / "golden_grocery_weeks"
BUNDLED_NLTK_DATA_DIR = REPO_ROOT / "resources" / "nltk_data"
