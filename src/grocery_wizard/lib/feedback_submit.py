"""Submit in-app feedback as GitHub inbox issues."""

from __future__ import annotations

from src.grocery_wizard.config import Config, load_config
from src.grocery_wizard.lib.feedback_github import create_feedback_issue

__all__ = ["submit_feedback"]


def submit_feedback(
    text: str,
    *,
    surface: str | None = None,
    config: Config | None = None,
) -> str:
    """File feedback via GitHub Issues API; returns a short user-facing outcome."""
    cfg = config or load_config()
    token = cfg.github_feedback_token
    repo = cfg.github_feedback_repository
    if not token or not repo:
        raise RuntimeError(
            "Feedback requires GITHUB_FEEDBACK_TOKEN and GITHUB_FEEDBACK_REPOSITORY "
            "(set in environment or repo-root secrets.toml)"
        )
    issue = create_feedback_issue(text, repository=repo, token=token, surface=surface)
    number = issue.get("number")
    if number is not None:
        return f"github #{number}"
    return "github"
