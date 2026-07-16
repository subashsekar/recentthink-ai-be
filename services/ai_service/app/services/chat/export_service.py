"""Export conversations and structured session content."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import MessageResponse, SessionDetailResponse, SessionSummaryResponse
from app.services.chat.message_metadata import should_hide_message
from app.services.chat.schemas import ChatExportRequest, ChatExportResponse, ExportFormat, ExportType
from app.services.history.history_manager import HistoryManager
from shared.exceptions.repository import RecordNotFoundError

if TYPE_CHECKING:
    pass


class ConversationExportService:
    """Unified export for chat sessions across AI products."""

    def __init__(
        self,
        *,
        history_manager: HistoryManager,
        session_repo: AISessionRepository,
        message_repo: AIMessageRepository,
    ) -> None:
        self._history = history_manager
        self._sessions = session_repo
        self._messages = message_repo

    def export_session(
        self,
        user: AuthenticatedUser,
        request: ChatExportRequest,
    ) -> ChatExportResponse:
        session = self._sessions.get_by_id(request.session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{request.session_id}' not found.")

        detail = self._history.get_session_detail(
            user,
            request.session_id,
            limit=10_000,
            offset=0,
            include_hidden=False,
        )
        all_messages = self._messages.list_all_by_session(request.session_id)
        visible_messages = [
            MessageResponse(
                id=message.id,
                role=message.role,
                module_name=message.module_name,
                content=message.content,
                content_metadata=message.content_metadata,
                created_at=message.created_at,
            )
            for message in all_messages
            if not should_hide_message(message.content_metadata, include_hidden=False)
        ]
        detail = SessionDetailResponse(
            session=detail.session,
            messages=visible_messages,
            total_messages=len(all_messages),
            memory=detail.memory,
            teacher_responses=detail.teacher_responses,
            follow_up_messages=detail.follow_up_messages,
        )

        safe_title = (
            "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (session.title or "conversation"))[:60]
            or "conversation"
        )

        if request.export_type == ExportType.CONVERSATION:
            body = self._conversation_markdown(detail.messages)
            if request.format == ExportFormat.JSON:
                payload = {
                    "session": detail.session.model_dump(mode="json"),
                    "messages": [message.model_dump(mode="json") for message in detail.messages],
                    "memory": detail.memory.model_dump(mode="json") if detail.memory else None,
                }
                return ChatExportResponse(
                    session_id=request.session_id,
                    format=ExportFormat.JSON,
                    export_type=request.export_type,
                    filename=f"{safe_title}.json",
                    content=json.dumps(payload, indent=2, default=str),
                    content_type="application/json",
                )
            if request.format == ExportFormat.TXT:
                return ChatExportResponse(
                    session_id=request.session_id,
                    format=ExportFormat.TXT,
                    export_type=request.export_type,
                    filename=f"{safe_title}.txt",
                    content=self._conversation_text(detail.messages),
                    content_type="text/plain",
                )
            if request.format == ExportFormat.PDF:
                from app.agents.course_generator.adapter import markdown_to_simple_pdf

                pdf_bytes = markdown_to_simple_pdf(body, title=session.title or "Conversation")
                return ChatExportResponse(
                    session_id=request.session_id,
                    format=ExportFormat.PDF,
                    export_type=request.export_type,
                    filename=f"{safe_title}.pdf",
                    content=pdf_bytes.decode("latin-1"),
                    content_type="application/pdf",
                )
            return ChatExportResponse(
                session_id=request.session_id,
                format=ExportFormat.MARKDOWN,
                export_type=request.export_type,
                filename=f"{safe_title}.md",
                content=body,
                content_type="text/markdown",
            )

        structured = self._extract_structured_payload(detail)
        if request.export_type == ExportType.SOLUTION:
            body = self._solution_markdown(structured, session.feature)
        elif request.export_type == ExportType.COURSE:
            body = self._course_markdown(structured, request.include)
        elif request.export_type == ExportType.PATTERN:
            body = self._pattern_markdown(structured, request.include)
        elif request.export_type == ExportType.INTERVIEW_REPORT:
            body = self._interview_markdown(structured, detail.messages)
        else:
            body = self._conversation_markdown(detail.messages)

        if request.format == ExportFormat.JSON:
            return ChatExportResponse(
                session_id=request.session_id,
                format=ExportFormat.JSON,
                export_type=request.export_type,
                filename=f"{safe_title}.json",
                content=json.dumps(structured or {}, indent=2, default=str),
                content_type="application/json",
            )
        if request.format == ExportFormat.TXT:
            return ChatExportResponse(
                session_id=request.session_id,
                format=ExportFormat.TXT,
                export_type=request.export_type,
                filename=f"{safe_title}.txt",
                content=body,
                content_type="text/plain",
            )
        if request.format == ExportFormat.PDF:
            from app.agents.course_generator.adapter import markdown_to_simple_pdf

            pdf_bytes = markdown_to_simple_pdf(body, title=session.title or safe_title)
            return ChatExportResponse(
                session_id=request.session_id,
                format=ExportFormat.PDF,
                export_type=request.export_type,
                filename=f"{safe_title}.pdf",
                content=pdf_bytes.decode("latin-1"),
                content_type="application/pdf",
            )
        return ChatExportResponse(
            session_id=request.session_id,
            format=ExportFormat.MARKDOWN,
            export_type=request.export_type,
            filename=f"{safe_title}.md",
            content=body,
            content_type="text/markdown",
        )

    @staticmethod
    def _conversation_markdown(messages) -> str:
        lines = ["# Conversation Export", ""]
        for message in messages:
            metadata = message.content_metadata or {}
            if should_hide_message(metadata, include_hidden=False):
                continue
            role = message.role.value if hasattr(message.role, "value") else str(message.role)
            lines.append(f"## {role.title()} — {message.created_at.isoformat()}")
            lines.append("")
            lines.append(message.content)
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _conversation_text(messages) -> str:
        lines: list[str] = []
        for message in messages:
            metadata = message.content_metadata or {}
            if should_hide_message(metadata, include_hidden=False):
                continue
            role = message.role.value if hasattr(message.role, "value") else str(message.role)
            lines.append(f"[{role}] {message.content}")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _extract_structured_payload(detail) -> dict:
        for message in reversed(detail.messages):
            metadata = message.content_metadata or {}
            structured = metadata.get("structured")
            if isinstance(structured, dict) and structured:
                return structured
        if detail.teacher_responses:
            last = detail.teacher_responses[-1]
            if last.structured:
                return last.structured
        if detail.memory and detail.memory.context:
            context = detail.memory.context
            if isinstance(context, dict):
                return context
        return {}

    @staticmethod
    def _solution_markdown(structured: dict, feature: AIFeature) -> str:
        coder = structured.get("coder") if isinstance(structured.get("coder"), dict) else structured
        teacher = structured.get("teacher") if isinstance(structured.get("teacher"), dict) else {}
        lines = [f"# {feature.value.replace('_', ' ').title()} Solution", ""]
        if teacher:
            lines.append("## Explanation")
            lines.append(json.dumps(teacher, indent=2))
            lines.append("")
        if coder:
            lines.append("## Code")
            lines.append(json.dumps(coder, indent=2))
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _course_markdown(structured: dict, include: list[str] | None) -> str:
        from app.agents.course_generator.adapter import content_to_markdown as course_to_markdown

        course = structured.get("course") if isinstance(structured.get("course"), dict) else structured
        if not course:
            return "# Course Export\n\n_No structured course content found._\n"
        try:
            from app.agents.course_generator.schemas import CourseContent

            content = CourseContent.model_validate(course)
            return course_to_markdown(content, include=include)
        except Exception:
            return "# Course Export\n\n```json\n" + json.dumps(course, indent=2) + "\n```\n"

    @staticmethod
    def _pattern_markdown(structured: dict, include: list[str] | None) -> str:
        from app.agents.dsa_pattern.adapter import content_to_markdown as pattern_to_markdown

        pattern = structured.get("dsa_pattern") if isinstance(structured.get("dsa_pattern"), dict) else structured
        if not pattern:
            return "# Pattern Export\n\n_No structured pattern content found._\n"
        try:
            from app.agents.dsa_pattern.schemas import PatternContent

            content = PatternContent.model_validate(pattern)
            return pattern_to_markdown(content, include=include)
        except Exception:
            return "# Pattern Export\n\n```json\n" + json.dumps(pattern, indent=2) + "\n```\n"

    @staticmethod
    def _interview_markdown(structured: dict, messages) -> str:
        lines = ["# Interview Report", ""]
        evaluator = structured.get("evaluator") if isinstance(structured.get("evaluator"), dict) else structured
        if evaluator:
            lines.append("## Evaluation")
            lines.append(json.dumps(evaluator, indent=2))
            lines.append("")
        lines.append("## Conversation")
        lines.append("")
        for message in messages:
            role = message.role.value if hasattr(message.role, "value") else str(message.role)
            lines.append(f"### {role.title()}")
            lines.append(message.content)
            lines.append("")
        return "\n".join(lines).strip() + "\n"
