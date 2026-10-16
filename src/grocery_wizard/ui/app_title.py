"""Decorative app title (word art) for the Streamlit shell."""

from __future__ import annotations

import streamlit as st

_APP_TITLE_HTML = """
<div class="gw-app-title-block">
  <h1 class="gw-app-title">
    <span class="gw-app-title__spark gw-app-title__spark--left" aria-hidden="true">✦</span>
    <span class="gw-app-title__grocery">Grocery</span>
    <span class="gw-app-title__wand" aria-hidden="true">
      <svg viewBox="0 0 48 48" role="img" aria-label="">
        <path class="gw-app-title__wand-stick" d="M8 40 L38 10" />
        <path
          class="gw-app-title__wand-star"
          d="M38 6 L40 12 L46 12 L41 16 L43 22 L38 18 L33 22 L35 16 L30 12 L36 12 Z"
        />
      </svg>
    </span>
    <span class="gw-app-title__wizard">Wizard</span>
    <span class="gw-app-title__spark gw-app-title__spark--right" aria-hidden="true">✦</span>
  </h1>
</div>
"""


def render_app_title() -> None:
    """Render the Grocery Wizard word-art title instead of plain ``st.title``."""
    st.markdown(_APP_TITLE_HTML, unsafe_allow_html=True)
