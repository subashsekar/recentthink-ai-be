"""SSE event builders for conversational chat streaming."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.utils.sse import format_sse_event


class ChatStreamStatus(StrEnum):
    THINKING = "thinking"
    PREPARING = "preparing"
    GENERATING = "generating"
    EXPLAINING = "explaining"
    EVALUATING = "evaluating"
    PRACTICE = "practice"
    COMPLETE = "complete"
    ERROR = "error"
    RECONNECT = "reconnect"


class SseEventCounter:
    """Per-stream incrementing SSE event ids for Last-Event-ID reconnect."""

    def __init__(self, start: int = 0) -> None:
        self._n = start

    def next(self) -> int:
        self._n += 1
        return self._n


def status_event(
    status: ChatStreamStatus,
    *,
    detail: str | None = None,
    event_id: int | str | None = None,
) -> str:
    payload: dict[str, Any] = {"type": "status", "status": status.value}
    if detail:
        payload["detail"] = detail
    return format_sse_event(payload, event_id=event_id)


def token_event(delta: str, *, event_id: int | str | None = None) -> str:
    return format_sse_event({"type": "token", "delta": delta}, event_id=event_id)


def complete_event(payload: dict[str, Any], *, event_id: int | str | None = None) -> str:
    return format_sse_event({"type": "complete", **payload}, event_id=event_id)


def error_event(
    message: str,
    *,
    code: str | None = None,
    event_id: int | str | None = None,
) -> str:
    body: dict[str, Any] = {"type": "error", "message": message}
    if code:
        body["code"] = code
    return format_sse_event(body, event_id=event_id)


def done_event(*, event_id: int | str | None = None) -> str:
    return format_sse_event({"type": "done"}, event_id=event_id)
