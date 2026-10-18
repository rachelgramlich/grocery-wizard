"""Every page in the picker renders and survives a Notion refresh (headless AppTest).

Runs in CI with the fake Notion DB from ``tests/conftest.py``. It checks real behavior:
the script runs and raises no exception, which source-text assertions cannot prove.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest
from ui_source import APP_PATH

from src.grocery_wizard.ui.ids import control_streamlit_key
from src.grocery_wizard.ui.views import (
    PAGE_LABEL_ADD,
    PAGE_LABEL_MAINTENANCE,
    PAGE_LABEL_PANTRY,
    PAGE_LABEL_WEEKLY,
    PAGE_PICKER_LABELS,
    page_slug_for_label,
)

pytestmark = pytest.mark.holistic_ui_smoke

REFRESH_LABEL = "Refresh from Notion"


def _open_page(label: str) -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)
    assert not at.exception, [e.value for e in at.exception]
    if label != PAGE_LABEL_WEEKLY:
        at.segmented_control[0].set_value(label).run(timeout=60)
    return at


def _exception_messages(at: AppTest) -> list[str]:
    return [str(e.value) for e in at.exception]


def test_picker_lists_every_page_this_suite_covers() -> None:
    assert set(PAGE_PICKER_LABELS) == {
        PAGE_LABEL_WEEKLY,
        PAGE_LABEL_ADD,
        PAGE_LABEL_PANTRY,
        PAGE_LABEL_MAINTENANCE,
    }


@pytest.mark.parametrize("label", PAGE_PICKER_LABELS)
def test_page_renders_without_exception(label: str) -> None:
    at = _open_page(label)
    assert not at.exception, _exception_messages(at)
    assert at.session_state["gw_render_page_slug"] == page_slug_for_label(label)


@pytest.mark.parametrize("label", PAGE_PICKER_LABELS)
def test_page_renders_visible_content(label: str) -> None:
    at = _open_page(label)
    rendered = [
        *(m.value for m in at.markdown if m.value),
        *(s.value for s in at.subheader if s.value),
        *(c.value for c in at.caption if c.value),
        *(b.label for b in at.button if b.label),
    ]
    page_body = [text for text in rendered if text.strip() and "gw-" not in text]
    assert len(page_body) > 3, f"{label!r} rendered almost nothing: {page_body}"


@pytest.mark.parametrize("label", PAGE_PICKER_LABELS)
def test_refresh_from_notion_keeps_page_and_does_not_raise(label: str) -> None:
    at = _open_page(label)
    refresh = [b for b in at.button if b.label == REFRESH_LABEL]
    assert refresh, f"{REFRESH_LABEL!r} button missing on {label!r}"
    refresh[0].click().run(timeout=60)
    assert not at.exception, _exception_messages(at)
    assert at.session_state["gw_render_page_slug"] == page_slug_for_label(label)


def test_switching_through_all_pages_in_one_session() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run(timeout=60)
    for label in (*PAGE_PICKER_LABELS, PAGE_LABEL_WEEKLY):
        at.segmented_control[0].set_value(label).run(timeout=60)
        assert not at.exception, f"{label}: {_exception_messages(at)}"
        assert at.session_state["gw_render_page_slug"] == page_slug_for_label(label)


def test_page_picker_session_key_matches_ids_module() -> None:
    from src.grocery_wizard.ui.ids import CONTROL_GLOBAL_PAGE_PICKER

    at = _open_page(PAGE_LABEL_PANTRY)
    assert control_streamlit_key(CONTROL_GLOBAL_PAGE_PICKER) in at.session_state
