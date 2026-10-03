"""Shared loading affordances for long-running Streamlit actions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import streamlit as st
from streamlit.runtime.scriptrunner_utils.script_run_context import (
    ThreadState,
    get_script_run_ctx,
)

GW_BUSY_MESSAGE_KEY = "gw_busy_message"
_BANNER_PLACEHOLDER_KEY = "gw_loading_banner_placeholder"


def mount_global_loading_banner() -> None:
    """Reserve a top-of-page slot; call once near the start of ``main()``."""
    # Streamlit ``DeltaGenerator`` slots are run-scoped — allocate fresh each rerun.
    st.session_state[_BANNER_PLACEHOLDER_KEY] = st.empty()


def _banner_placeholder() -> st.delta_generator.DeltaGenerator | None:
    slot = st.session_state.get(_BANNER_PLACEHOLDER_KEY)
    return slot if slot is not None else None


def _can_update_global_banner() -> bool:
    """Fragment reruns cannot write to the app-level banner slot created in ``main()``."""
    ctx = get_script_run_ctx(suppress_warning=True)
    if ctx is None:
        return False
    if ctx.fragment_ids_this_run:
        return False
    if ThreadState.get().fragment_id is not None:
        return False
    return _banner_placeholder() is not None


def _refresh_global_banner() -> None:
    if not _can_update_global_banner():
        return
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


def run_with_loading[T](message: str, action: Callable[[], T]) -> T:
    """Run ``action`` inside :func:`loading_indicator`."""
    with loading_indicator(message):
        return action()
