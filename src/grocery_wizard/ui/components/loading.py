"""Shared loading affordances for long-running Streamlit actions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import streamlit as st
from streamlit.runtime.scriptrunner_utils.script_run_context import (
    ThreadState,
    get_script_run_ctx,
)

_BANNER_PLACEHOLDER_KEY = "gw_loading_banner_placeholder"


def clear_global_loading_banner() -> None:
    """Clear the top loading slot (e.g. before inline spinners on the weekly plan)."""
    if not _can_update_global_banner():
        return
    placeholder = _banner_placeholder()
    if placeholder is not None:
        placeholder.empty()


def mount_global_loading_banner() -> None:
    """Reserve a top-of-page slot; call once near the start of ``main()``."""
    # Streamlit ``DeltaGenerator`` slots are run-scoped — allocate fresh each rerun.
    st.session_state[_BANNER_PLACEHOLDER_KEY] = st.empty()
    clear_global_loading_banner()


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


@contextmanager
def loading_indicator(message: str, *, use_global_banner: bool = False) -> Iterator[None]:
    """Show a Streamlit spinner while work runs.

    By default, spinners render inline in the active block (next to the control you used).
    Pass ``use_global_banner=True`` only for **Refresh from Notion** (top slot under the title).
    Fragment reruns always use inline ``st.spinner`` (the top slot is not writable).
    """
    if use_global_banner and _can_update_global_banner():
        placeholder = _banner_placeholder()
        assert placeholder is not None
        with placeholder.container(), st.spinner(message):
            yield
    else:
        with st.spinner(message):
            yield


def run_with_loading[T](
    message: str,
    action: Callable[[], T],
    *,
    use_global_banner: bool = False,
) -> T:
    """Run ``action`` inside :func:`loading_indicator`."""
    with loading_indicator(message, use_global_banner=use_global_banner):
        return action()
