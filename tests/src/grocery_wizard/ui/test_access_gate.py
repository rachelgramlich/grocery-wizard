"""Tests for email allowlist parsing."""

from __future__ import annotations

from src.grocery_wizard.ui.access_gate import parse_email_allowlist


def test_parse_email_allowlist_normalizes() -> None:
    allowlist = parse_email_allowlist(" Alice@Example.com , bob@example.com , ")
    assert allowlist == frozenset({"alice@example.com", "bob@example.com"})


def test_parse_email_allowlist_empty() -> None:
    assert parse_email_allowlist(None) == frozenset()
    assert parse_email_allowlist("  ,  ") == frozenset()
