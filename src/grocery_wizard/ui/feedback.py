"""Streamlit control for capturing free-text feedback to a local backlog file."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.lib.feedback_backlog import append_feedback

_FEEDBACK_NOTE_KEY = "gw_feedback_note"
_FEEDBACK_FLASH_OK = "gw_feedback_flash_ok"
_FEEDBACK_WARN_EMPTY = "gw_feedback_warn_empty"


def _submit_feedback(*, surface: str | None) -> None:
    """Button callback — runs before widgets on the next rerun."""
    text = st.session_state.get(_FEEDBACK_NOTE_KEY, "").strip()
    if not text:
        st.session_state[_FEEDBACK_WARN_EMPTY] = True
        return

    append_feedback(text, surface=surface)
    st.session_state[_FEEDBACK_FLASH_OK] = True
    st.session_state[_FEEDBACK_NOTE_KEY] = ""


def render_feedback_controls(*, surface: str | None = None) -> None:
    """Global feedback expander; writes append-only JSON Lines under ``.local/``."""
    with st.expander("Send feedback", expanded=False):
        st.caption("Bugs, ideas, and papercuts — saved locally on this machine for later triage.")
        if st.session_state.pop(_FEEDBACK_FLASH_OK, False):
            st.success("Thanks — your note was saved.")
            st.toast("Feedback saved", icon="✅")
        if st.session_state.pop(_FEEDBACK_WARN_EMPTY, False):
            st.warning("Please enter a short note before submitting.")

        st.text_area(
            "Your note",
            key=_FEEDBACK_NOTE_KEY,
            height=100,
            label_visibility="collapsed",
            placeholder="Describe a bug, idea, or papercut…",
        )
        st.button(
            "Submit feedback",
            key="gw_feedback_submit",
            type="secondary",
            on_click=_submit_feedback,
            kwargs={"surface": surface},
        )
