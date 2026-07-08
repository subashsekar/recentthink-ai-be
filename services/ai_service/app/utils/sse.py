"""Server-Sent Events formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def format_sse_event(payload: dict[str, Any]) -> str:
    """Serialize a payload as a single SSE data frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
