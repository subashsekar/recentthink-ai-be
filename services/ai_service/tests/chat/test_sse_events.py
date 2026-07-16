"""Chat router and SSE helper tests."""

from __future__ import annotations

import json

from app.services.chat.schemas import ChatFeatureSlug, FEATURE_SLUG_MAP
from app.services.chat.sse_events import (
    ChatStreamStatus,
    complete_event,
    done_event,
    error_event,
    status_event,
    token_event,
)


def test_feature_slug_map_covers_all_products() -> None:
    assert set(FEATURE_SLUG_MAP) == set(ChatFeatureSlug)
    assert len(FEATURE_SLUG_MAP) == 5


def test_sse_event_payload_shapes() -> None:
    status = json.loads(status_event(ChatStreamStatus.GENERATING).removeprefix("data: ").strip())
    status_detail = json.loads(
        status_event(ChatStreamStatus.PREPARING, detail="loading").removeprefix("data: ").strip(),
    )
    token = json.loads(token_event("abc").removeprefix("data: ").strip())
    complete = json.loads(
        complete_event({"session_id": "x", "status": "COMPLETED"}).removeprefix("data: ").strip(),
    )
    error = json.loads(error_event("boom", code="E1").removeprefix("data: ").strip())
    done = json.loads(done_event().removeprefix("data: ").strip())

    assert status["type"] == "status"
    assert status["status"] == "generating"
    assert status_detail["detail"] == "loading"
    assert token == {"type": "token", "delta": "abc"}
    assert complete["type"] == "complete"
    assert error["code"] == "E1"
    assert done["type"] == "done"


def test_sse_event_ids_are_emitted() -> None:
    frame = status_event(ChatStreamStatus.THINKING, event_id=7)
    assert frame.startswith("id: 7\n")
    assert "data: " in frame
    payload = json.loads(frame.split("data: ", 1)[1].strip())
    assert payload["status"] == "thinking"
