"""Streamlit-only grocery list UI helpers."""

from __future__ import annotations

import html
import json

import streamlit as st

from src.grocery_wizard.ui.theme import GW_THEME


def render_copy_button(
    text: str,
    *,
    label: str = "Copy",
    key: str,
) -> None:
    """Render a full-width control that copies ``text`` to the clipboard."""
    payload = json.dumps(text)
    label_json = json.dumps(label)
    copied_json = json.dumps("Copied!")
    safe_label = html.escape(label)
    tokens = GW_THEME
    st.iframe(
        f"""
        <style>
          .gw-copy-btn {{
            width: 100%;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.5rem;
            background: {tokens.accent};
            color: {tokens.on_accent};
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
          }}
          .gw-copy-btn:hover {{
            filter: brightness(1.05);
          }}
        </style>
        <button id="gw-copy-{key}" type="button" class="gw-copy-btn">{safe_label}</button>
        <script>
          (function () {{
            const btn = document.getElementById("gw-copy-{key}");
            const text = {payload};
            const label = {label_json};
            const copied = {copied_json};
            btn.addEventListener("click", function () {{
              navigator.clipboard.writeText(text).then(function () {{
                btn.textContent = copied;
                setTimeout(function () {{ btn.textContent = label; }}, 2000);
              }});
            }});
          }})();
        </script>
        """,
        height=52,
    )
    st.caption("Select-all in the text area above, or use Copy for the same text.")
