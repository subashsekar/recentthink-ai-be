"""Session history manager."""

from __future__ import annotations

from uuid import UUID

from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.enums import AIFeature, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.conversation_memory_repository import ConversationMemoryRepository
from app.schemas.ai import (
    ConversationMemoryResponse,
    HistoryListResponse,
    MessageResponse,
    ModuleResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
)
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError


class HistoryManager:
    """Reusable history layer with owner validation and admin access."""

    def __init__(
        self,
        *,
        session_repo: AISessionRepository,
        message_repo: AIMessageRepository,
        memory_repo: ConversationMemoryRepository | None = None,
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._memory = memory_repo

    def _ensure_access(self, user: AuthenticatedUser, session: AISession) -> None:
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")

    @staticmethod
    def _to_summary(session: AISession) -> SessionSummaryResponse:
        return SessionSummaryResponse(
            id=session.id,
            feature=session.feature,
            title=session.title,
            status=session.status,
            summary=session.summary,
            model_id=session.model_id,
            mode_id=session.mode_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def _to_message(message: AIMessage) -> MessageResponse:
        return MessageResponse(
            id=message.id,
            role=message.role,
            module_name=message.module_name,
            content=message.content,
            content_metadata=message.content_metadata,
            created_at=message.created_at,
        )

    @staticmethod
    def _to_teacher_response(message: AIMessage) -> ModuleResponse:
        metadata = message.content_metadata or {}
        return ModuleResponse(
            module=ModuleName.TEACHER,
            content=message.content,
            structured=metadata.get("structured"),
            metadata={"cards": metadata.get("cards")},
        )

    def list_history(
        self,
        user: AuthenticatedUser,
        *,
        feature: AIFeature | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> HistoryListResponse:
        if user.role in {"ADMIN", "SUPER_ADMIN"}:
            sessions = self._sessions.list_all(
                feature=feature,
                search=search,
                limit=limit,
                offset=offset,
            )
            total = len(sessions)
        else:
            sessions = self._sessions.list_by_user(
                user.user_id,
                feature=feature,
                search=search,
                limit=limit,
                offset=offset,
            )
            total = self._sessions.count_by_user(user.user_id, feature=feature)

        return HistoryListResponse(
            sessions=[self._to_summary(session) for session in sessions],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_session_detail(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> SessionDetailResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        messages = self._messages.list_by_session(session_id, limit=limit, offset=offset)

        teacher_responses = [
            self._to_teacher_response(msg)
            for msg in messages
            if msg.module_name == ModuleName.TEACHER
        ]
        follow_up_messages = [
            self._to_message(msg)
            for msg in messages
            if msg.role.value == "user" and (msg.content_metadata or {}).get("follow_up_intent")
        ]

        memory_response = None
        if self._memory is not None:
            record = self._memory.get_by_session_id(session_id)
            if record is not None:
                memory_response = ConversationMemoryResponse(
                    session_id=record.session_id,
                    summary=record.summary or record.history_summary,
                    context=record.context,
                    recent_messages=record.recent_messages,
                    previous_responses=record.previous_responses,
                    follow_up_questions=record.follow_up_questions,
                    memory_version=record.memory_version,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )

        return SessionDetailResponse(
            session=self._to_summary(session),
            messages=[self._to_message(message) for message in messages],
            total_messages=len(messages),
            memory=memory_response,
            teacher_responses=teacher_responses,
            follow_up_messages=follow_up_messages,
        )

    def delete_session(self, user: AuthenticatedUser, session_id: UUID) -> None:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        self._sessions.delete_session(session_id)
