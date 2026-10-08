"""Tests for weekly plan date rules and naming."""

from __future__ import annotations

from datetime import date

from src.grocery_wizard.planning.saved_weekly_plans import (
    canonical_plan_name,
    needs_save_week_choice,
    saved_plan_week_start,
    week_start_sunday,
)


def test_canonical_plan_name() -> None:
    assert canonical_plan_name(date(2026, 9, 13)) == "2026-09-13_plan"


def test_week_start_sunday() -> None:
    assert week_start_sunday(date(2026, 9, 13)) == date(2026, 9, 13)  # Sunday
    assert week_start_sunday(date(2026, 9, 14)) == date(2026, 9, 13)  # Monday
    assert week_start_sunday(date(2026, 9, 15)) == date(2026, 9, 13)  # Tuesday


def test_today_and_yesterday_share_week_start() -> None:
    monday = date(2026, 9, 14)
    sunday = date(2026, 9, 13)
    assert week_start_sunday(monday) == week_start_sunday(sunday)


def test_needs_save_week_choice_tuesday_wednesday_only() -> None:
    assert needs_save_week_choice(date(2026, 9, 15)) is True  # Tue
    assert needs_save_week_choice(date(2026, 9, 16)) is True  # Wed
    assert needs_save_week_choice(date(2026, 9, 14)) is False  # Mon
    assert needs_save_week_choice(date(2026, 9, 17)) is False  # Thu


def test_saved_plan_week_start_thu_through_mon() -> None:
    assert saved_plan_week_start(date(2026, 9, 17)) == date(2026, 9, 20)  # Thu → upcoming Sun
    assert saved_plan_week_start(date(2026, 9, 14)) == date(2026, 9, 13)  # Mon → current Sun
    assert saved_plan_week_start(date(2026, 9, 13)) == date(2026, 9, 13)  # Sun


def test_saved_plan_week_start_tuesday_requires_choice() -> None:
    tuesday = date(2026, 9, 15)
    assert saved_plan_week_start(tuesday, week_choice="this_week") == date(2026, 9, 13)
    assert saved_plan_week_start(tuesday, week_choice="next_week") == date(2026, 9, 20)
