"""Create GitHub issues for in-app feedback (deployed / shared Streamlit)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

FEEDBACK_GITHUB_INBOX_LABEL = "user-feedback-inbox"
MAX_FEEDBACK_BODY_CHARS = 4000
_GITHUB_API = "https://api.github.com"


def _issue_title(text: str) -> str:
    one_line = " ".join(text.split())
    prefix = "User feedback: "
    max_len = 80
    room = max_len - len(prefix)
    if len(one_line) <= room:
        return f"{prefix}{one_line}"
    return f"{prefix}{one_line[: room - 1].rstrip()}…"


def _issue_body(*, text: str, surface: str | None, timestamp: str) -> str:
    lines = [f"**Submitted:** {timestamp}"]
    if surface:
        lines.append(f"**Surface:** {surface}")
    footer = "_Auto-filed from Grocery Wizard (FEEDBACK_MODE=github)._"
    lines.extend(["", text.rstrip(), "", "---", footer])
    body = "\n".join(lines)
    if len(body) > MAX_FEEDBACK_BODY_CHARS:
        raise ValueError(f"feedback body exceeds {MAX_FEEDBACK_BODY_CHARS} characters")
    return body


def create_feedback_issue(
    text: str,
    *,
    repository: str,
    token: str,
    surface: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Open a GitHub issue in ``owner/repo`` with the inbox label."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("feedback text must be non-empty after stripping")

    repo = repository.strip().strip("/")
    if repo.count("/") != 1:
        raise ValueError("GITHUB_FEEDBACK_REPOSITORY must be owner/repo")

    when = timestamp or datetime.now(tz=UTC).isoformat()
    payload = {
        "title": _issue_title(cleaned),
        "body": _issue_body(text=cleaned, surface=surface, timestamp=when),
        "labels": [FEEDBACK_GITHUB_INBOX_LABEL],
    }
    url = f"{_GITHUB_API}/repos/{repo}/issues"
    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason
        raise RuntimeError(f"GitHub issue create failed ({response.status_code}): {detail}")
    return response.json()
