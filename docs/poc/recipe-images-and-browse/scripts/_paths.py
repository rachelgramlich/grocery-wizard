"""Paths for Browse / image-fetch POC scripts (not shipped product code)."""

from __future__ import annotations

from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = POC_ROOT / "data"
OUT_DIR = POC_ROOT / "out"


def repo_root() -> Path:
    try:
        from src.grocery_wizard.paths import REPO_ROOT

        return REPO_ROOT
    except ImportError:
        return POC_ROOT.parents[2]


REPO_ROOT = repo_root()