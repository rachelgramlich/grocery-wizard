"""Google OIDC gate for household Streamlit deploys."""

from __future__ import annotations

import streamlit as st

from src.grocery_wizard.config import Config, load_config


def parse_email_allowlist(raw: str | None) -> frozenset[str]:
    """Parse comma-separated emails (case-insensitive)."""
    if not raw or not raw.strip():
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def enforce_access_gate(config: Config | None = None) -> None:
    """Require Google login and an allowlisted email when auth is enabled."""
    cfg = config or load_config()
    if not cfg.require_auth:
        return

    allowlist = parse_email_allowlist(cfg.auth_email_allowlist)
    if not allowlist:
        st.error(
            "App auth is misconfigured: set GROCERY_WIZARD_AUTH_EMAIL_ALLOWLIST "
            "when GROCERY_WIZARD_REQUIRE_AUTH is true."
        )
        st.stop()

    if not st.user.is_logged_in:
        st.login()
        st.stop()

    email = (st.user.email or "").strip().lower()
    if email not in allowlist:
        st.error("This Google account is not authorized to use Grocery Wizard.")
        st.button("Log out", on_click=st.logout)
        st.stop()
