"""Touch-friendly dismissal for select / multiselect menus (#440)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import streamlit as st

_STATIC_DIR: Final[Path] = Path(__file__).resolve().parent / "static"
DROPDOWN_DISMISS_JS: Final[Path] = _STATIC_DIR / "dropdown_dismiss.js"
_SESSION_KEY: Final[str] = "_gw_dropdown_dismiss_installed"


def dropdown_dismiss_iframe_html() -> str:
    """HTML for a 1px iframe that installs the dismiss handlers in the parent document.

    The script is copied into a ``<script>`` tag owned by the parent document so the
    listeners outlive this iframe (Streamlit drops it on the next rerun).
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
    """Install the parent-document handlers once per browser session."""
    if st.session_state.get(_SESSION_KEY):
        return
    st.session_state[_SESSION_KEY] = True
    st.iframe(dropdown_dismiss_iframe_html(), height=1)
