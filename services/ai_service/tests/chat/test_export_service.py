"""Conversation export service tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import MessageResponse, ModuleResponse, SessionDetailResponse, SessionSummaryResponse
from app.services.chat.export_service import ConversationExportService
from app.services.chat.schemas import ChatExportRequest, ExportFormat, ExportType
from app.services.history.history_manager import HistoryManager


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


def _detail(session_id) -> SessionDetailResponse:
    return SessionDetailResponse(
        session=SessionSummaryResponse(
            id=session_id,
            feature=AIFeature.LEETCODE,
            title="Two Sum",
            status=SessionStatus.COMPLETED,
            summary=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        messages=[
            MessageResponse(
                id=uuid4(),
                role=MessageRole.ASSISTANT,
                module_name=ModuleName.TEACHER,
                content="Explanation",
                content_metadata={
                    "structured": {
                        "teacher": {"explanation": "Use hash map"},
                        "coder": {"optimal_solution": {"code": "def solve(): pass"}},
                    },
                },
                created_at=datetime.now(UTC),
            ),
        ],
        total_messages=1,
        teacher_responses=[
            ModuleResponse(
                module=ModuleName.TEACHER,
                content="Explanation",
                structured={"teacher": {"explanation": "Use hash map"}},
            ),
        ],
    )


def test_export_solution_json(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.title = "Two Sum"
    session.feature = AIFeature.LEETCODE

    history = MagicMock()
    history.get_session_detail.return_value = _detail(session_id)
    export = ConversationExportService(
        history_manager=history,
        session_repo=MagicMock(get_by_id=MagicMock(return_value=session)),
        message_repo=MagicMock(
            list_all_by_session=MagicMock(return_value=_detail(session_id).messages),
        ),
    )
    result = export.export_session(
        user,
        ChatExportRequest(
            session_id=session_id,
            format=ExportFormat.JSON,
            export_type=ExportType.SOLUTION,
        ),
    )
    payload = json.loads(result.content)
    assert "teacher" in payload or "coder" in payload


def test_export_txt_and_skip_deleted_messages(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.title = "Chat"
    session.feature = AIFeature.INTERVIEW

    detail = _detail(session_id)
    detail.messages.append(
        MessageResponse(
            id=uuid4(),
            role=MessageRole.USER,
            module_name=None,
            content="hidden",
            content_metadata={"deleted": True},
            created_at=datetime.now(UTC),
        ),
    )
    history = MagicMock()
    history.get_session_detail.return_value = detail
    export = ConversationExportService(
        history_manager=history,
        session_repo=MagicMock(get_by_id=MagicMock(return_value=session)),
        message_repo=MagicMock(list_all_by_session=MagicMock(return_value=detail.messages)),
    )
    result = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.TXT),
    )
    assert "hidden" not in result.content
    assert result.format == ExportFormat.TXT


def test_export_conversation_pdf(monkeypatch, user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.title = "Two Sum"
    session.feature = AIFeature.LEETCODE

    history = MagicMock()
    history.get_session_detail.return_value = _detail(session_id)

    def fake_pdf(markdown: str, *, title: str) -> bytes:
        return b"%PDF-fake"

    monkeypatch.setattr(
        "app.agents.course_generator.adapter.markdown_to_simple_pdf",
        fake_pdf,
    )

    export = ConversationExportService(
        history_manager=history,
        session_repo=MagicMock(get_by_id=MagicMock(return_value=session)),
        message_repo=MagicMock(
            list_all_by_session=MagicMock(return_value=_detail(session_id).messages),
        ),
    )
    result = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.PDF),
    )
    assert result.format == ExportFormat.PDF
    assert result.content_type == "application/pdf"
    assert result.filename.endswith(".pdf")


def test_export_full_session_beyond_page_limit(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.title = "Long Chat"
    session.feature = AIFeature.LEETCODE

    messages = []
    for index in range(150):
        messages.append(
            MessageResponse(
                id=uuid4(),
                role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
                module_name=ModuleName.TEACHER if index % 2 else None,
                content=f"message-{index}",
                content_metadata={},
                created_at=datetime.now(UTC),
            ),
        )

    history = MagicMock()
    history.get_session_detail.return_value = SessionDetailResponse(
        session=_detail(session_id).session,
        messages=messages[:100],
        total_messages=150,
    )
    export = ConversationExportService(
        history_manager=history,
        session_repo=MagicMock(get_by_id=MagicMock(return_value=session)),
        message_repo=MagicMock(list_all_by_session=MagicMock(return_value=messages)),
    )
    result = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.TXT),
    )
    assert "message-149" in result.content
    assert result.content.count("message-") >= 150
