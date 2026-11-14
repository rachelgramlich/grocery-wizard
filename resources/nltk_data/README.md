# Bundled NLTK data

`ingredient-parser-nlp` needs the English POS tagger **`averaged_perceptron_tagger_eng`**. Streamlit Community Cloud does not keep NLTK’s download cache across cold starts, so we vendor it here instead of fetching at runtime.

To refresh after an `nltk` upgrade:

```bash
uv run python -c "import nltk; from pathlib import Path; d=Path('resources/nltk_data'); d.mkdir(parents=True, exist_ok=True); nltk.download('averaged_perceptron_tagger_eng', download_dir=str(d))"
```

Commit updated files under `taggers/averaged_perceptron_tagger_eng/`.
