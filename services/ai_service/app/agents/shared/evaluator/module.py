"""Evaluator processing module — stores analysis, no additional LLM calls."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.enums import MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.schemas.ai import ModuleResponse


class EvaluatorModule:
    """Read evaluator JSON and format feedback."""

    def process(
        self,
        *,
        session_id: UUID,
        payload: dict[str, Any],
        message_repo: AIMessageRepository | None = None,
    ) -> ModuleResponse:
        time_complexity = payload.get("time_complexity", "Unknown")
        space_complexity = payload.get("space_complexity", "Unknown")
        optimizations = payload.get("optimizations") or []
        mistakes = payload.get("mistakes") or []
        edge_cases = payload.get("edge_cases") or []
        feedback = str(payload.get("feedback", ""))
        follow_ups = payload.get("follow_up_questions") or payload.get("interview_questions") or []
        analytics = payload.get("analytics") or {}

        parts = [
            "## Evaluation",
            f"**Time Complexity:** {time_complexity}",
            f"**Space Complexity:** {space_complexity}",
        ]
        if feedback:
            parts.append(f"\n{feedback}")
        if optimizations:
            parts.append("\n### Optimizations")
            parts.extend(f"- {item}" for item in optimizations)
        if mistakes:
            parts.append("\n### Common Mistakes")
            parts.extend(f"- {item}" for item in mistakes)
        if edge_cases:
            parts.append("\n### Edge Cases")
            parts.extend(f"- {item}" for item in edge_cases)
        if follow_ups:
            parts.append("\n### Interview Follow-ups")
            parts.extend(f"- {question}" for question in follow_ups)

        content = "\n".join(parts).strip() or "No evaluator output available."

        if message_repo is not None:
            message_repo.create_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                module_name=ModuleName.EVALUATOR,
                content_metadata={
                    "structured": payload,
                    "analytics": analytics,
                    "markdown": content,
                },
            )

        return ModuleResponse(
            module=ModuleName.EVALUATOR,
            content=content,
            structured=payload,
            metadata={"analytics": analytics},
        )
