"""Bundled NLTK data for ingredient-parser-nlp (Streamlit Cloud has no warm cache)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLED_NLTK_DATA = _REPO_ROOT / "resources" / "nltk_data"
_TAGGER_RESOURCE = "taggers/averaged_perceptron_tagger_eng"

_nltk_ready = False


@lru_cache(maxsize=1)
def bundled_nltk_data_dir() -> Path | None:
    """Return repo-root ``resources/nltk_data`` when the tagger corpus is present."""
    tagger_dir = _BUNDLED_NLTK_DATA / _TAGGER_RESOURCE
    if tagger_dir.is_dir():
        return _BUNDLED_NLTK_DATA
    return None


def ensure_nltk_data() -> None:
    """Load the English POS tagger from the repo bundle, else download once."""
    global _nltk_ready  # noqa: PLW0603
    if _nltk_ready:
        return
    import nltk

    bundled = bundled_nltk_data_dir()
    if bundled is not None:
        bundled_str = str(bundled)
        if bundled_str not in nltk.data.path:
            nltk.data.path.insert(0, bundled_str)
    try:
        nltk.data.find(_TAGGER_RESOURCE)
    except LookupError:
        nltk.download("averaged_perceptron_tagger_eng", quiet=True)
    _nltk_ready = True
