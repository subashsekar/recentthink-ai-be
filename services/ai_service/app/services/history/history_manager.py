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
from app.services.chat.message_metadata import should_hide_message
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
        model_id = session.model_id if isinstance(session.model_id, str) else None
        mode_id = session.mode_id if isinstance(session.mode_id, str) else None
        return SessionSummaryResponse(
            id=session.id,
            feature=session.feature,
            title=session.title,
            status=session.status,
            summary=session.summary,
            model_id=model_id,
            mode_id=mode_id,
            is_archived=bool(getattr(session, "is_archived", False)),
            is_pinned=bool(getattr(session, "is_pinned", False)),
            last_active_at=getattr(session, "last_active_at", None),
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
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> HistoryListResponse:
        if user.role in {"ADMIN", "SUPER_ADMIN"}:
            sessions = self._sessions.list_all(
                feature=feature,
                search=search,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
            total = len(sessions)
        else:
            sessions = self._sessions.list_by_user(
                user.user_id,
                feature=feature,
                search=search,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
            total = self._sessions.count_by_user(
                user.user_id,
                feature=feature,
                include_archived=include_archived,
            )

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
        include_hidden: bool = False,
    ) -> SessionDetailResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        messages = self._messages.list_by_session(session_id, limit=limit, offset=offset)
        total_messages = self._messages.count_by_session(session_id)

        visible_messages = [
            message
            for message in messages
            if not should_hide_message(message.content_metadata, include_hidden=include_hidden)
        ]

        teacher_responses = [
            self._to_teacher_response(msg)
            for msg in visible_messages
            if msg.module_name == ModuleName.TEACHER
        ]
        follow_up_messages = [
            self._to_message(msg)
            for msg in visible_messages
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
            messages=[self._to_message(message) for message in visible_messages],
            total_messages=total_messages,
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

    def rename_session(self, user: AuthenticatedUser, session_id: UUID, *, title: str) -> SessionSummaryResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        updated = self._sessions.update_session(session_id, title=title.strip())
        return self._to_summary(updated)

    def archive_session(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        archived: bool = True,
    ) -> SessionSummaryResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        updated = self._sessions.update_session(session_id, is_archived=archived)
        return self._to_summary(updated)

    def pin_session(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        pinned: bool = True,
    ) -> SessionSummaryResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        self._ensure_access(user, session)
        updated = self._sessions.update_session(session_id, is_pinned=pinned)
        return self._to_summary(updated)

    def touch_session(self, session_id: UUID) -> None:
        self._sessions.touch_last_active(session_id)
