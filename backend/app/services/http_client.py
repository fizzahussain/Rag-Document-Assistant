"""Shared async HTTP client for AI provider calls (connection reuse)."""

from __future__ import annotations

import httpx

from backend.app.config import settings

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a process-wide AsyncClient, creating it on first use."""

    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
        )
    return _client


async def close_http_client() -> None:
    """Close the shared client on application shutdown."""

    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
