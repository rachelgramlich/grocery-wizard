"""Shared loading affordances for long-running Streamlit actions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar

import streamlit as st

GW_BUSY_MESSAGE_KEY = "gw_busy_message"
_BANNER_PLACEHOLDER_KEY = "gw_loading_banner_placeholder"

_T = TypeVar("_T")


def mount_global_loading_banner() -> None:
    """Reserve a top-of-page slot; call once near the start of ``main()``."""
    # Streamlit ``DeltaGenerator`` slots are run-scoped — allocate fresh each rerun.
    st.session_state[_BANNER_PLACEHOLDER_KEY] = st.empty()


def _banner_placeholder() -> st.delta_generator.DeltaGenerator | None:
    slot = st.session_state.get(_BANNER_PLACEHOLDER_KEY)
    return slot if slot is not None else None


def _refresh_global_banner() -> None:
    placeholder = _banner_placeholder()
    if placeholder is None:
        return
    message = st.session_state.get(GW_BUSY_MESSAGE_KEY)
    if message:
        with placeholder.container():
            st.status(str(message), state="running", expanded=False)
    else:
        placeholder.empty()


@contextmanager
def loading_indicator(message: str) -> Iterator[None]:
    """Show a global status banner and inline spinner while ``message`` work runs."""
    st.session_state[GW_BUSY_MESSAGE_KEY] = message
    _refresh_global_banner()
    try:
        with st.spinner(message):
            yield
    finally:
        st.session_state.pop(GW_BUSY_MESSAGE_KEY, None)
        _refresh_global_banner()


def run_with_loading(message: str, action: Callable[[], _T]) -> _T:
    """Run ``action`` inside :func:`loading_indicator`."""
    with loading_indicator(message):
        return action()
