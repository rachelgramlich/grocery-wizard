"""Tests for GitHub feedback issue creation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.grocery_wizard.lib.feedback_github import (
    FEEDBACK_GITHUB_INBOX_LABEL,
    create_feedback_issue,
)


def test_create_feedback_issue_posts_inbox_label(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str, *, json: dict[str, object], headers: dict[str, str], timeout: int
    ) -> MagicMock:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        response = MagicMock()
        response.status_code = 201
        response.text = ""
        response.json.return_value = {"number": 99}
        return response

    monkeypatch.setattr("src.grocery_wizard.lib.feedback_github.requests.post", fake_post)

    result = create_feedback_issue(
        "Pantry page is slow",
        repository="owner/repo",
        token="ghp_test",
        surface="pantry",
        timestamp="2026-01-01T00:00:00+00:00",
    )

    assert result["number"] == 99
    assert captured["url"] == "https://api.github.com/repos/owner/repo/issues"
    payload = captured["json"]
    assert payload["labels"] == [FEEDBACK_GITHUB_INBOX_LABEL]
    assert "Pantry page is slow" in str(payload["body"])
    assert "**Surface:** pantry" in str(payload["body"])
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer ghp_test"


def test_create_feedback_issue_rejects_bad_repository() -> None:
    with pytest.raises(ValueError, match="owner/repo"):
        create_feedback_issue("x", repository="not-a-repo", token="t")
