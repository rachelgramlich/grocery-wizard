"""Paths for Browse / image-fetch POC scripts (not shipped product code)."""

from __future__ import annotations

from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = POC_ROOT / "data"
OUT_DIR = POC_ROOT / "out"
REPO_ROOT = POC_ROOT.parents[2]  # docs/poc/recipe-images-and-browse → repo root
