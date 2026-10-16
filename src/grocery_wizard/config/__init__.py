"""Environment configuration for Grocery Wizard."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent

# Committed package configuration (store aisles only).
CONFIG_DIR = Path(__file__).resolve().parent
STORE_AISLES_PATH = CONFIG_DIR / "store_aisles.txt"

# Per-week local runtime data (gitignored via .local/).
DATA_DIR = Path(".local/grocery_wizard")
LEGACY_DATA_DIR = Path(".grocery_wizard")

WEEK_PLAN_PATH = DATA_DIR / "week_plan.json"
LEGACY_WEEK_PLAN_PATH = LEGACY_DATA_DIR / "week_plan.json"
NYT_LAST_SYNC_PATH = DATA_DIR / "nyt_last_sync.json"
_REPO_SECRETS_PATH = _REPO_ROOT / "secrets.toml"
_LEGACY_STREAMLIT_SECRETS_PATH = _REPO_ROOT / ".streamlit" / "secrets.toml"
_STREAMLIT_SECRETS_SYMLINK = _LEGACY_STREAMLIT_SECRETS_PATH
_DEFAULT_GITHUB_FEEDBACK_REPOSITORY = "rachelgramlich/grocery-wizard"


class Config(BaseSettings):
    """Notion and Grocery Wizard settings loaded from environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    notion_api_key: str = Field(validation_alias="NOTION_API_KEY")
    notion_recipe_database_id: str = Field(
        validation_alias=AliasChoices("NOTION_RECIPE_DATABASE_ID", "NOTION_DATABASE_ID"),
    )
    notion_pantry_database_id: str = Field(validation_alias="NOTION_PANTRY_DATABASE_ID")
    notion_recurring_weekly_database_id: str = Field(
        validation_alias="NOTION_RECURRING_WEEKLY_DATABASE_ID",
    )
    notion_weekly_meal_plans_database_id: str = Field(
        validation_alias="NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID",
    )
    default_meals: int = Field(default=7, validation_alias="GROCERY_WIZARD_DEFAULT_MEALS")
    dev_ui_enabled: bool = Field(default=False, validation_alias="GROCERY_WIZARD_DEV_UI")
    notion_data_source_id: str | None = Field(
        default=None,
        validation_alias="NOTION_DATA_SOURCE_ID",
    )
    name_column: str | None = Field(default=None, validation_alias="GROCERY_WIZARD_NAME_COLUMN")
    link_column: str | None = Field(default=None, validation_alias="GROCERY_WIZARD_LINK_COLUMN")
    ingredients_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_INGREDIENTS_COLUMN",
    )
    instructions_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_INSTRUCTIONS_COLUMN",
    )
    nyt_synced_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_NYT_SYNCED_COLUMN",
    )
    suggestion_rejections_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_SUGGESTION_REJECTIONS_COLUMN",
    )
    plan_selections_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_PLAN_SELECTIONS_COLUMN",
    )
    meal_plan_status_column: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_MEAL_PLAN_STATUS_COLUMN",
    )
    github_feedback_token: str | None = Field(
        default=None,
        validation_alias="GITHUB_FEEDBACK_TOKEN",
    )
    github_feedback_repository: str = Field(
        default=_DEFAULT_GITHUB_FEEDBACK_REPOSITORY,
        validation_alias="GITHUB_FEEDBACK_REPOSITORY",
    )
    require_auth: bool = Field(default=False, validation_alias="GROCERY_WIZARD_REQUIRE_AUTH")
    auth_email_allowlist: str | None = Field(
        default=None,
        validation_alias="GROCERY_WIZARD_AUTH_EMAIL_ALLOWLIST",
    )

    @field_validator(
        "notion_api_key",
        "notion_recipe_database_id",
        "notion_pantry_database_id",
        "notion_recurring_weekly_database_id",
        "notion_weekly_meal_plans_database_id",
        "notion_data_source_id",
        "name_column",
        "link_column",
        "ingredients_column",
        "instructions_column",
        "nyt_synced_column",
        "suggestion_rejections_column",
        "plan_selections_column",
        "meal_plan_status_column",
        "github_feedback_token",
        "github_feedback_repository",
        "auth_email_allowlist",
        mode="before",
    )
    @classmethod
    def _strip_string(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("notion_api_key")
    @classmethod
    def _require_api_key(cls, value: str | None) -> str:
        if not value:
            raise ValueError("NOTION_API_KEY is required (set in .env or Cloud Agent Secrets)")
        return value

    @field_validator("notion_recipe_database_id")
    @classmethod
    def _require_recipe_database_id(cls, value: str | None) -> str:
        if not value:
            raise ValueError(
                "NOTION_RECIPE_DATABASE_ID is required (set in .env or Cloud Agent Secrets)"
            )
        return value

    @field_validator("notion_pantry_database_id")
    @classmethod
    def _require_pantry_database_id(cls, value: str | None) -> str:
        if not value:
            raise ValueError(
                "NOTION_PANTRY_DATABASE_ID is required (set in .env or Cloud Agent Secrets)"
            )
        return value

    @field_validator("notion_recurring_weekly_database_id")
    @classmethod
    def _require_recurring_database_id(cls, value: str | None) -> str:
        if not value:
            raise ValueError(
                "NOTION_RECURRING_WEEKLY_DATABASE_ID is required "
                "(set in .env or Cloud Agent Secrets)"
            )
        return value

    @field_validator("notion_weekly_meal_plans_database_id")
    @classmethod
    def _require_weekly_plans_database_id(cls, value: str | None) -> str:
        if not value:
            raise ValueError(
                "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID is required "
                "(set in .env or Cloud Agent Secrets)"
            )
        return value


def _secrets_toml_path() -> Path | None:
    """Repo-root ``secrets.toml`` first, then legacy ``.streamlit/secrets.toml``."""
    if _REPO_SECRETS_PATH.is_file():
        return _REPO_SECRETS_PATH
    if _LEGACY_STREAMLIT_SECRETS_PATH.is_file():
        return _LEGACY_STREAMLIT_SECRETS_PATH
    return None


def ensure_streamlit_secrets_symlink() -> None:
    """Link ``.streamlit/secrets.toml`` to repo-root ``secrets.toml`` for Streamlit auth."""
    if not _REPO_SECRETS_PATH.is_file():
        return
    _STREAMLIT_SECRETS_SYMLINK.parent.mkdir(parents=True, exist_ok=True)
    desired = _REPO_SECRETS_PATH.resolve()
    if _STREAMLIT_SECRETS_SYMLINK.is_symlink():
        if _STREAMLIT_SECRETS_SYMLINK.resolve() == desired:
            return
        _STREAMLIT_SECRETS_SYMLINK.unlink()
    elif _STREAMLIT_SECRETS_SYMLINK.is_file():
        return
    _STREAMLIT_SECRETS_SYMLINK.symlink_to("../secrets.toml")


def _apply_streamlit_secrets_to_environ() -> None:
    """Inject flat keys from repo-root ``secrets.toml`` (Streamlit + local parity).

    Precedence when ``Config`` loads: process environment, then secrets.toml, then ``.env``.
    Nested tables (e.g. ``[auth]``) are for Streamlit OIDC only and are not mapped here.
    """
    path = _secrets_toml_path()
    if path is None:
        return
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    for key, value in raw.items():
        if isinstance(value, dict):
            continue
        env_key = str(key)
        if isinstance(value, bool):
            os.environ.setdefault(env_key, "true" if value else "false")
        else:
            os.environ.setdefault(env_key, str(value))


def load_config() -> Config:
    """Load configuration from environment, repo-root ``secrets.toml``, and ``.env``."""
    _apply_streamlit_secrets_to_environ()
    try:
        return Config()
    except ValidationError as exc:
        for error in exc.errors():
            loc = error.get("loc", ())
            if "notion_api_key" in loc:
                raise ValueError(
                    "NOTION_API_KEY is required (set in .env or Cloud Agent Secrets)"
                ) from exc
            if "notion_recipe_database_id" in loc:
                raise ValueError(
                    "NOTION_RECIPE_DATABASE_ID is required (set in .env or Cloud Agent Secrets)"
                ) from exc
            if "notion_pantry_database_id" in loc:
                raise ValueError(
                    "NOTION_PANTRY_DATABASE_ID is required (set in .env or Cloud Agent Secrets)"
                ) from exc
            if "notion_recurring_weekly_database_id" in loc:
                raise ValueError(
                    "NOTION_RECURRING_WEEKLY_DATABASE_ID is required "
                    "(set in .env or Cloud Agent Secrets)"
                ) from exc
            if "notion_weekly_meal_plans_database_id" in loc:
                raise ValueError(
                    "NOTION_WEEKLY_MEAL_PLANS_DATABASE_ID is required "
                    "(set in .env or Cloud Agent Secrets)"
                ) from exc
        raise
