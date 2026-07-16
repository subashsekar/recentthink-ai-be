"""Shared assistant message version-history helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.models.enums import MessageRole


class _MessageLike(Protocol):
    id: UUID
    role: MessageRole | str
    created_at: datetime
    content_metadata: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class VersionHistoryRecord:
    """Neutral version-history row mapped by feature schemas."""

    message_id: UUID
    created_at: datetime
    status: str
    regenerated_from_message_id: UUID | None
    is_current: bool


def build_assistant_version_history(messages: list[_MessageLike]) -> list[VersionHistoryRecord]:
    """Build regenerate-chain history from assistant messages in a session."""
    assistants = [message for message in messages if message.role == MessageRole.ASSISTANT]
    if not assistants:
        return []

    current_id = assistants[-1].id
    items: list[VersionHistoryRecord] = []
    for message in assistants:
        metadata = message.content_metadata or {}
        status = str(metadata.get("status") or "completed")
        regenerated_from = metadata.get("regenerated_from_message_id")
        regenerated_uuid: UUID | None = None
        if regenerated_from:
            try:
                regenerated_uuid = UUID(str(regenerated_from))
            except ValueError:
                regenerated_uuid = None
        items.append(
            VersionHistoryRecord(
                message_id=message.id,
                created_at=message.created_at,
                status=status,
                regenerated_from_message_id=regenerated_uuid,
                is_current=message.id == current_id and status.lower() not in {"superseded", "failed"},
            ),
        )
    return items
