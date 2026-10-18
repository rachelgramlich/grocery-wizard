"""Refresh-from-Notion and picker integrity smoke (headless AppTest).

Primary page open + body checks live in ``test_holistic_ui_smoke_apptest.py``
(``just smoke-ui``). This file keeps refresh-per-page, one-session page
switching, and ids-module alignment — behavior source-text tests cannot prove.
"""

from __future__ import annotations

import pytest
from ui_source import (
    apptest_assert_no_exception,
    apptest_open_page,
    apptest_start_app,
)

from src.grocery_wizard.ui.ids import control_streamlit_key
from src.grocery_wizard.ui.views import (
    PAGE_LABEL_ADD,
    PAGE_LABEL_MAINTENANCE,
    PAGE_LABEL_PANTRY,
    PAGE_LABEL_WEEKLY,
    PAGE_PICKER_LABELS,
    page_slug_for_label,
)

REFRESH_LABEL = "Refresh from Notion"


def test_picker_lists_every_page_this_suite_covers() -> None:
    assert set(PAGE_PICKER_LABELS) == {
        PAGE_LABEL_WEEKLY,
        PAGE_LABEL_ADD,
        PAGE_LABEL_PANTRY,
        PAGE_LABEL_MAINTENANCE,
    }


@pytest.mark.parametrize("label", PAGE_PICKER_LABELS)
def test_refresh_from_notion_keeps_page_and_does_not_raise(label: str) -> None:
    at = apptest_start_app()
    apptest_open_page(at, label)
    refresh = [b for b in at.button if b.label == REFRESH_LABEL]
    assert refresh, f"{REFRESH_LABEL!r} button missing on {label!r}"
    refresh[0].click().run(timeout=60)
    apptest_assert_no_exception(at, context=f"refresh on {label!r}")
    assert at.session_state["gw_render_page_slug"] == page_slug_for_label(label)


def test_switching_through_all_pages_in_one_session() -> None:
    at = apptest_start_app()
    for label in (*PAGE_PICKER_LABELS, PAGE_LABEL_WEEKLY):
        apptest_open_page(at, label)
        apptest_assert_no_exception(at, context=label)
        assert at.session_state["gw_render_page_slug"] == page_slug_for_label(label)


def test_page_picker_session_key_matches_ids_module() -> None:
    from src.grocery_wizard.ui.ids import CONTROL_GLOBAL_PAGE_PICKER

    at = apptest_start_app()
    apptest_open_page(at, PAGE_LABEL_PANTRY)
    assert control_streamlit_key(CONTROL_GLOBAL_PAGE_PICKER) in at.session_state
