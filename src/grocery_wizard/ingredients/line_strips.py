"""Leading-token strips shared by storage parsing and grocery junk checks."""

from __future__ import annotations

import re


def _strip_optional_prefix(text: str) -> str:
    return re.sub(r"^optional:\s*", "", text, flags=re.IGNORECASE).strip()


def _strip_or_prefix(text: str) -> str:
    if text.lower().startswith("or "):
        return text[3:].strip()
    return text


def _strip_leading_to_prefix(text: str) -> str:
    return re.sub(r"^to\s+(?=\d)", "", text, flags=re.IGNORECASE).strip()
