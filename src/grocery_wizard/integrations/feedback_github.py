"""Create GitHub issues for in-app feedback (deployed / shared Streamlit)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

FEEDBACK_GITHUB_INBOX_LABEL = "user-feedback-inbox"
MAX_FEEDBACK_BODY_CHARS = 4000
_DEBUG_LOG_JSON_FENCE_OPEN = "```json\n"
_DEBUG_LOG_JSON_FENCE_CLOSE = "\n```"
_DEBUG_LOG_TRUNCATION_NOTE = (
    "\n\n_(Debug log JSON truncated to fit GitHub issue size limits. "
    "Use the Notion link above or the download control in the app for the full log.)_"
)
_GITHUB_API = "https://api.github.com"


def _issue_title(text: str) -> str:
    one_line = " ".join(text.split())
    prefix = "User feedback: "
    max_len = 80
    room = max_len - len(prefix)
    if len(one_line) <= room:
        return f"{prefix}{one_line}"
    return f"{prefix}{one_line[: room - 1].rstrip()}…"


def _issue_body_shell(*, surface: str | None, timestamp: str) -> tuple[list[str], str]:
    lines = [f"**Submitted:** {timestamp}"]
    if surface:
        lines.append(f"**Surface:** {surface}")
    footer = "_Auto-filed from Grocery Wizard Send feedback._"
    return lines, footer


def _issue_body_for_text(*, text: str, surface: str | None, timestamp: str) -> str:
    header_lines, footer = _issue_body_shell(surface=surface, timestamp=timestamp)
    lines = [*header_lines, "", text.rstrip(), "", "---", footer]
    return "\n".join(lines)


def _truncate_debug_log_json_in_text(
    text: str,
    *,
    surface: str | None,
    timestamp: str,
) -> str | None:
    open_idx = text.find(_DEBUG_LOG_JSON_FENCE_OPEN)
    if open_idx < 0:
        return None
    close_idx = text.find(_DEBUG_LOG_JSON_FENCE_CLOSE, open_idx + len(_DEBUG_LOG_JSON_FENCE_OPEN))
    if close_idx < 0:
        return None
    prefix = text[: open_idx + len(_DEBUG_LOG_JSON_FENCE_OPEN)]
    suffix = text[close_idx:]
    json_start = open_idx + len(_DEBUG_LOG_JSON_FENCE_OPEN)
    json_blob = text[json_start:close_idx]
    if not json_blob:
        return None
    for length in range(len(json_blob), 0, -1):
        candidate = f"{prefix}{json_blob[:length].rstrip()}…{_DEBUG_LOG_TRUNCATION_NOTE}{suffix}"
        if len(_issue_body_for_text(text=candidate, surface=surface, timestamp=timestamp)) <= (
            MAX_FEEDBACK_BODY_CHARS
        ):
            return candidate
    return f"{prefix}…{_DEBUG_LOG_TRUNCATION_NOTE}{suffix}"


def fit_feedback_text_to_issue_body(
    text: str,
    *,
    surface: str | None,
    timestamp: str,
) -> str:
    """Shrink embedded debug JSON so the GitHub issue body stays under the cap."""
    trimmed = text.rstrip()
    if len(_issue_body_for_text(text=trimmed, surface=surface, timestamp=timestamp)) <= (
        MAX_FEEDBACK_BODY_CHARS
    ):
        return trimmed

    truncated = _truncate_debug_log_json_in_text(trimmed, surface=surface, timestamp=timestamp)
    if truncated is not None:
        trimmed = truncated
        if len(_issue_body_for_text(text=trimmed, surface=surface, timestamp=timestamp)) <= (
            MAX_FEEDBACK_BODY_CHARS
        ):
            return trimmed

    note_cap = MAX_FEEDBACK_BODY_CHARS - 200
    if len(trimmed) > note_cap:
        trimmed = trimmed[: note_cap - 1].rstrip() + "…"
    while (
        len(_issue_body_for_text(text=trimmed, surface=surface, timestamp=timestamp))
        > MAX_FEEDBACK_BODY_CHARS
        and len(trimmed) > 1
    ):
        trimmed = trimmed[: max(1, len(trimmed) * 9 // 10)].rstrip() + "…"
    return trimmed


def _issue_body(*, text: str, surface: str | None, timestamp: str) -> str:
    fitted = fit_feedback_text_to_issue_body(text, surface=surface, timestamp=timestamp)
    body = _issue_body_for_text(text=fitted, surface=surface, timestamp=timestamp)
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
