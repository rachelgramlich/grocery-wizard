"""Streamlit control for capturing free-text feedback."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.lib.feedback_submit import submit_feedback
from src.grocery_wizard.ui.ids import control_streamlit_key

_FEEDBACK_NOTE_KEY = "gw_feedback_note"
_FEEDBACK_FLASH_OK = "gw_feedback_flash_ok"
_FEEDBACK_WARN_EMPTY = "gw_feedback_warn_empty"
_FEEDBACK_ERROR_KEY = "gw_feedback_error"
_FEEDBACK_SUBMIT_KEY = "gw_feedback_submit"


def _grocery_debug_log_url_from_session() -> str | None:
    result = st.session_state.get("grocery_result")
    if not isinstance(result, dict):
        return None
    url = result.get("debug_log_notion_url")
    return str(url).strip() if url else None


def _submit_feedback(*, surface: str | None) -> None:
    """Button callback — runs before widgets on the next rerun."""
    text = st.session_state.get(_FEEDBACK_NOTE_KEY, "").strip()
    if not text:
        st.session_state[_FEEDBACK_WARN_EMPTY] = True
        return

    log_url = _grocery_debug_log_url_from_session()
    if log_url:
        text = f"{text.rstrip()}\n\n**Latest grocery list debug log (Notion):** {log_url}"

    try:
        outcome = submit_feedback(text, surface=surface)
    except (RuntimeError, ValueError) as exc:
        st.session_state[_FEEDBACK_ERROR_KEY] = str(exc)
        return

    st.session_state[_FEEDBACK_FLASH_OK] = outcome
    st.session_state[_FEEDBACK_NOTE_KEY] = ""


def _render_feedback_form(*, surface: str | None) -> None:
    flash = st.session_state.pop(_FEEDBACK_FLASH_OK, False)
    if flash:
        st.success(f"Thanks — your note was filed ({flash}).")
        st.toast("Feedback submitted", icon="✅")
    if st.session_state.pop(_FEEDBACK_WARN_EMPTY, False):
        st.warning("Please enter a short note before submitting.")
    if err := st.session_state.pop(_FEEDBACK_ERROR_KEY, None):
        st.error(err)

    st.text_area(
        "Your note",
        key=_FEEDBACK_NOTE_KEY,
        height=100,
        max_chars=4000,
        label_visibility="collapsed",
        placeholder="Describe a bug, feature request, idea, or question...",
    )
    st.button(
        "Submit feedback",
        key=_FEEDBACK_SUBMIT_KEY,
        type="secondary",
        on_click=_submit_feedback,
        kwargs={"surface": surface},
    )


def render_feedback_controls(
    *,
    surface: str | None = None,
    control_id: str | None = None,
) -> None:
    """Global feedback popover; ``surface`` is usually the active page slug."""
    widget_key = control_streamlit_key(control_id) if control_id else "gw_feedback"
    with st.popover(
        "Send feedback",
        key=widget_key,
        type="secondary",
        use_container_width=True,
    ):
        _render_feedback_form(surface=surface)
