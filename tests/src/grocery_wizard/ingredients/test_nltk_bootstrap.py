"""NLTK tagger is bundled so Streamlit Cloud does not download at runtime."""

from __future__ import annotations

import nltk

from src.grocery_wizard.ingredients import nltk_bootstrap
from src.grocery_wizard.ingredients.nltk_bootstrap import bundled_nltk_data_dir, ensure_nltk_data


def test_bundled_nltk_tagger_present() -> None:
    data_dir = bundled_nltk_data_dir()
    assert data_dir is not None
    ensure_nltk_data()
    nltk.data.find("taggers/averaged_perceptron_tagger_eng")


def test_ensure_nltk_data_uses_bundle_without_download(monkeypatch) -> None:
    calls: list[str] = []

    def _fake_download(pkg: str, *, quiet: bool = False) -> None:
        calls.append(pkg)

    monkeypatch.setattr(nltk, "download", _fake_download)
    nltk_bootstrap._nltk_ready = False
    ensure_nltk_data()
    assert calls == []
