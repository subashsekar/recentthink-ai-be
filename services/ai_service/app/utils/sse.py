"""Server-Sent Events formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def format_sse_event(
    payload: dict[str, Any],
    *,
    event_id: int | str | None = None,
) -> str:
    """Serialize a payload as a single SSE data frame.

    When ``event_id`` is provided, emits an ``id:`` line so clients can
    reconnect with ``Last-Event-ID``.
    """
    data = json.dumps(payload, ensure_ascii=False, default=str)
    if event_id is None:
        return f"data: {data}\n\n"
    return f"id: {event_id}\ndata: {data}\n\n"
