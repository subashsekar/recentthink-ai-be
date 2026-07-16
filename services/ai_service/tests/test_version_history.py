"""Unit tests for shared assistant version-history helper."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import MessageRole
from app.utils.version_history import build_assistant_version_history


def test_build_assistant_version_history_marks_current_and_links() -> None:
    older_id = uuid4()
    newer_id = uuid4()
    messages = [
        SimpleNamespace(
            id=uuid4(),
            role=MessageRole.USER,
            created_at=datetime.now(UTC),
            content_metadata={},
        ),
        SimpleNamespace(
            id=older_id,
            role=MessageRole.ASSISTANT,
            created_at=datetime.now(UTC),
            content_metadata={
                "status": "superseded",
            },
        ),
        SimpleNamespace(
            id=newer_id,
            role=MessageRole.ASSISTANT,
            created_at=datetime.now(UTC),
            content_metadata={
                "status": "completed",
                "regenerated_from_message_id": str(older_id),
            },
        ),
    ]

    records = build_assistant_version_history(messages)
    assert len(records) == 2
    assert records[0].message_id == older_id
    assert records[0].is_current is False
    assert records[1].message_id == newer_id
    assert records[1].is_current is True
    assert records[1].regenerated_from_message_id == older_id


def test_build_assistant_version_history_empty() -> None:
    assert build_assistant_version_history([]) == []
