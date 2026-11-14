"""Tests for attaching grocery list debug logs to feedback."""

from __future__ import annotations

from src.grocery_wizard.integrations.feedback_github import (
    MAX_FEEDBACK_BODY_CHARS,
    _issue_body_for_text,
    fit_feedback_text_to_issue_body,
)
from src.grocery_wizard.integrations.feedback_list_log import enrich_feedback_with_list_debug_log
from src.grocery_wizard.shopping.list_log import ListTrace, build_list_log


def test_enrich_feedback_includes_json_and_notion_link() -> None:
    trace = ListTrace()
    log = build_list_log(
        trace,
        meals=["Soup"],
        exclude_pantry=False,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=["flour"],
    )
    text = enrich_feedback_with_list_debug_log(
        "Wrong aisle for cheese",
        debug_log=log,
        notion_url="https://www.notion.so/logpage",
    )
    assert "Wrong aisle for cheese" in text
    assert "https://www.notion.so/logpage" in text
    assert '"final_list"' in text
    assert "```json" in text


def test_enrich_feedback_unchanged_without_log() -> None:
    assert (
        enrich_feedback_with_list_debug_log("Just a note", debug_log=None, notion_url=None)
        == "Just a note"
    )


def test_fit_feedback_text_truncates_large_debug_json() -> None:
    trace = ListTrace()
    huge_lines = [f"item {index}" for index in range(500)]
    log = build_list_log(
        trace,
        meals=["Big week"],
        exclude_pantry=False,
        excluded_pantry=[],
        missing_ingredients=[],
        item_provenance={},
        extra_items=[],
        final_items=huge_lines,
    )
    enriched = enrich_feedback_with_list_debug_log(
        "List looked wrong",
        debug_log=log,
        notion_url="https://www.notion.so/logpage",
    )
    fitted = fit_feedback_text_to_issue_body(
        enriched,
        surface="weekly",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    body = _issue_body_for_text(
        text=fitted, surface="weekly", timestamp="2026-01-01T00:00:00+00:00"
    )
    assert len(body) <= MAX_FEEDBACK_BODY_CHARS
    assert "truncated to fit GitHub issue size limits" in fitted
