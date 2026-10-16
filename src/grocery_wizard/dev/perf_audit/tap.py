"""Notion API tap: time and count reads, stub and count writes (never writes to Notion)."""

from __future__ import annotations

import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import notion_client.client as notion_client_module
import requests.sessions

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)
_READ_SUFFIXES = ("/query", "/search")
_WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})
DEFAULT_WRITE_LATENCY_S = 0.4
_SAFE_EXTERNAL_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class ExternalCallBlockedError(RuntimeError):
    """Raised when a scenario tries to reach a non-Notion service in safe mode."""


def normalize_endpoint(method: str, path: str) -> str:
    """Return a stable label such as ``POST /data_sources/{id}/query``."""
    return f"{method.upper()} {_UUID_RE.sub('{id}', path.split('?', 1)[0])}"


def is_write_request(method: str, path: str) -> bool:
    if method.upper() not in _WRITE_METHODS:
        return False
    return not path.split("?", 1)[0].endswith(_READ_SUFFIXES)


def _echo_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Turn request-shaped Notion properties into response-shaped ones for stubbed writes."""
    echoed: dict[str, Any] = {}
    for name, value in properties.items():
        if not isinstance(value, dict) or not value:
            continue
        kind = next(iter(value))
        payload = value[kind]
        if kind in ("title", "rich_text") and isinstance(payload, list):
            payload = [
                {"plain_text": (item.get("text") or {}).get("content", ""), **item}
                for item in payload
            ]
        echoed[name] = {"type": kind, kind: payload}
    return echoed


def stub_write_response(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
    """Fabricate a minimal Notion response for an intercepted write."""
    clean = path.split("?", 1)[0].rstrip("/")
    properties = _echo_properties((body or {}).get("properties") or {})
    segments = clean.split("/")
    page_id = segments[-1] if len(segments) > 1 and segments[-2] == "pages" else "stub-page-id"
    if clean.endswith("/pages") or "/pages/" in clean:
        return {"object": "page", "id": page_id, "properties": properties}
    return {"object": "stub", "id": "stub-id", "properties": properties}


@dataclass
class CallRecord:
    endpoint: str
    seconds: float
    write: bool
    stubbed: bool


@dataclass
class TapSnapshot:
    reads: int = 0
    read_seconds: float = 0.0
    writes: int = 0
    by_endpoint: dict[str, int] = field(default_factory=dict)
    external_calls: int = 0
    external_seconds: float = 0.0
    external_hosts: dict[str, int] = field(default_factory=dict)


@dataclass
class ExternalRecord:
    host: str
    seconds: float


class NotionTap:
    """Patch ``notion_client.Client.request`` and ``requests`` for one audit session."""

    def __init__(self, *, stub_writes: bool = True, allow_external: bool = False) -> None:
        self.stub_writes = stub_writes
        self.allow_external = allow_external
        self.records: list[CallRecord] = []
        self.blocked_external: list[str] = []
        self.external_records: list[ExternalRecord] = []
        self._read_latencies: list[float] = []
        self._orig_request: Any = None
        self._orig_session_request: Any = None

    def install(self) -> None:
        tap = self
        client_cls = notion_client_module.Client
        self._orig_request = client_cls.request

        def request(
            client: Any,
            path: str,
            method: str,
            query: dict[str, Any] | None = None,
            body: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> Any:
            endpoint = normalize_endpoint(method, path)
            write = is_write_request(method, path)
            if write and tap.stub_writes:
                tap.records.append(CallRecord(endpoint, 0.0, write=True, stubbed=True))
                return stub_write_response(method, path, body)
            start = time.perf_counter()
            try:
                return tap._orig_request(client, path, method, query, body, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                tap.records.append(CallRecord(endpoint, elapsed, write=write, stubbed=False))
                if not write:
                    tap._read_latencies.append(elapsed)

        client_cls.request = request

        self._orig_session_request = requests.sessions.Session.request

        def session_request(session: Any, method: str, url: str, **kwargs: Any) -> Any:
            if method.upper() not in _SAFE_EXTERNAL_METHODS and not tap.allow_external:
                tap.blocked_external.append(f"{method.upper()} {url}")
                raise ExternalCallBlockedError(
                    f"Blocked mutating external call in safe mode: {method} {url}"
                )
            host = urlparse(url).netloc or "unknown"
            start = time.perf_counter()
            try:
                return tap._orig_session_request(session, method, url, **kwargs)
            finally:
                tap.external_records.append(ExternalRecord(host, time.perf_counter() - start))

        requests.sessions.Session.request = session_request

    def uninstall(self) -> None:
        if self._orig_request is not None:
            notion_client_module.Client.request = self._orig_request
            self._orig_request = None
        if self._orig_session_request is not None:
            requests.sessions.Session.request = self._orig_session_request
            self._orig_session_request = None

    def mark(self) -> tuple[int, int]:
        """Position to pass to :meth:`since` later."""
        return len(self.records), len(self.external_records)

    def since(self, mark: tuple[int, int]) -> TapSnapshot:
        notion_mark, external_mark = mark
        window = self.records[notion_mark:]
        external = self.external_records[external_mark:]
        reads = [r for r in window if not r.write]
        writes = [r for r in window if r.write]
        counts = Counter(r.endpoint for r in window)
        return TapSnapshot(
            reads=len(reads),
            read_seconds=sum(r.seconds for r in reads),
            writes=len(writes),
            by_endpoint=dict(counts.most_common()),
            external_calls=len(external),
            external_seconds=sum(r.seconds for r in external),
            external_hosts=dict(Counter(r.host for r in external).most_common()),
        )

    def median_read_latency(self) -> float:
        if not self._read_latencies:
            return DEFAULT_WRITE_LATENCY_S
        return statistics.median(self._read_latencies)
