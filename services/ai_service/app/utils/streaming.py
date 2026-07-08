"""Streaming detection helpers."""

from __future__ import annotations

from fastapi import Request


def should_stream(request: Request) -> bool:
    """Return True when the request indicates a streaming response is desired."""
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept.lower():
        return True
    stream = request.query_params.get("stream")
    return bool(stream and stream.lower() in {"1", "true", "yes"})
