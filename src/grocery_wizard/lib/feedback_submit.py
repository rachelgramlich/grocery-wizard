"""Route in-app feedback to local backlog or GitHub inbox."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from src.grocery_wizard.config import FEEDBACK_BACKLOG_PATH, Config, load_config
from src.grocery_wizard.lib.feedback_backlog import append_feedback
from src.grocery_wizard.lib.feedback_github import create_feedback_issue

FeedbackMode = Literal["local", "github"]

__all__ = ["FeedbackMode", "submit_feedback"]


def submit_feedback(
    text: str,
    *,
    surface: str | None = None,
    config: Config | None = None,
    local_path: Path = FEEDBACK_BACKLOG_PATH,
) -> str:
    """Persist feedback per ``FEEDBACK_MODE``; returns a short user-facing outcome."""
    cfg = config or load_config()
    mode = cfg.feedback_mode

    if mode == "local":
        append_feedback(text, path=local_path, surface=surface)
        return "local"

    if mode == "github":
        token = cfg.github_feedback_token
        repo = cfg.github_feedback_repository
        if not token or not repo:
            raise RuntimeError(
                "FEEDBACK_MODE=github requires GITHUB_FEEDBACK_TOKEN and GITHUB_FEEDBACK_REPOSITORY"
            )
        issue = create_feedback_issue(text, repository=repo, token=token, surface=surface)
        number = issue.get("number")
        if number is not None:
            return f"github #{number}"
        return "github"

    raise RuntimeError(f"Unsupported FEEDBACK_MODE: {mode!r}")
