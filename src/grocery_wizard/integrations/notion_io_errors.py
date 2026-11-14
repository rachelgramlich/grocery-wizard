"""Exception types for broad-but-intentional Notion / HTTP boundary catches."""

from __future__ import annotations

from notion_client.errors import APIResponseError
from requests import RequestException

# Network/API/user-data faults we swallow at UI or batch-job boundaries (log + continue).
NOTION_BOUNDARY_ERRORS: tuple[type[Exception], ...] = (
    APIResponseError,
    RequestException,
    OSError,
    ValueError,
    KeyError,
    TypeError,
    RuntimeError,
)
