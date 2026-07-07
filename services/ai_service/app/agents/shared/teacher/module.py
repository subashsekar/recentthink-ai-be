"""Teacher processing module — formats LLM JSON, no additional LLM calls."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.shared.teacher.formatter import TeacherFormatter
from app.agents.shared.teacher.schemas import TeacherOutput
from app.models.enums import MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.schemas.ai import ModuleResponse


class TeacherModule:
    """Read teacher JSON, format markdown and cards, store history. Never calls OpenRouter."""

    def __init__(self, formatter: TeacherFormatter | None = None) -> None:
        self._formatter = formatter or TeacherFormatter()

    def process(
        self,
        *,
        session_id: UUID,
        payload: dict[str, Any],
        message_repo: AIMessageRepository | None = None,
    ) -> ModuleResponse:
        teacher_output = TeacherOutput.from_payload(payload)
        content, cards = self._formatter.format(teacher_output)
        structured = teacher_output.model_dump()

        if message_repo is not None:
            message_repo.create_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                module_name=ModuleName.TEACHER,
                content_metadata={
                    "structured": structured,
                    "markdown": content,
                    "cards": [card.model_dump() for card in cards],
                },
            )

        return ModuleResponse(
            module=ModuleName.TEACHER,
            content=content,
            structured=structured,
            metadata={"cards": [card.model_dump() for card in cards]},
        )
