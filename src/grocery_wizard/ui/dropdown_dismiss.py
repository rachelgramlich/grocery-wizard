"""Touch-friendly dismissal for popovers, select, and multiselect menus (#440)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import streamlit as st

_STATIC_DIR: Final[Path] = Path(__file__).resolve().parent / "static"
DROPDOWN_DISMISS_JS: Final[Path] = _STATIC_DIR / "dropdown_dismiss.js"


def dropdown_dismiss_iframe_html() -> str:
    """HTML for a 1px iframe that installs the dismiss handlers in the parent document.

    The script is copied into a ``<script>`` tag owned by the parent document so the
    listeners outlive this iframe. The script guards itself against double install, so
    this is safe to render on every rerun (and survives page reloads and new sessions).
    """
    code = json.dumps(DROPDOWN_DISMISS_JS.read_text(encoding="utf-8"))
    return f"""
    <script>
    (function () {{
      var parentDoc = window.parent.document;
      var script = parentDoc.createElement("script");
      script.textContent = {code};
      parentDoc.head.appendChild(script);
      script.remove();
    }})();
    </script>
    """


def install_dropdown_dismiss() -> None:
    """Install the parent-document handlers (idempotent in the browser)."""
    st.iframe(dropdown_dismiss_iframe_html(), height=1)
