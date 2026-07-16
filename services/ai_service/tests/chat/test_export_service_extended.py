"""Additional export service coverage tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import ConversationMemoryResponse, MessageResponse, SessionDetailResponse, SessionSummaryResponse
from app.services.chat.export_service import ConversationExportService
from app.services.chat.schemas import ChatExportRequest, ExportFormat, ExportType
from shared.exceptions.repository import RecordNotFoundError


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


def _service(*, session, messages, detail: SessionDetailResponse | None = None):
    history = MagicMock()
    history.get_session_detail.return_value = detail or SessionDetailResponse(
        session=SessionSummaryResponse(
            id=session.id,
            feature=session.feature,
            title=session.title,
            status=SessionStatus.COMPLETED,
            summary=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        messages=messages,
        total_messages=len(messages),
    )
    return ConversationExportService(
        history_manager=history,
        session_repo=MagicMock(get_by_id=MagicMock(return_value=session)),
        message_repo=MagicMock(list_all_by_session=MagicMock(return_value=messages)),
    )


def test_export_session_not_found(user: AuthenticatedUser) -> None:
    export = ConversationExportService(
        history_manager=MagicMock(),
        session_repo=MagicMock(get_by_id=MagicMock(return_value=None)),
        message_repo=MagicMock(),
    )
    with pytest.raises(RecordNotFoundError):
        export.export_session(user, ChatExportRequest(session_id=uuid4(), format=ExportFormat.MARKDOWN))


def test_export_solution_markdown(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock(id=session_id, title="Two Sum", feature=AIFeature.LEETCODE)
    messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="Explanation",
            content_metadata={
                "structured": {
                    "teacher": {"explanation": "hash map"},
                    "coder": {"optimal_solution": {"code": "def solve(): pass"}},
                },
            },
            created_at=datetime.now(UTC),
        ),
    ]
    export = _service(session=session, messages=messages)
    result = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.SOLUTION),
    )
    assert "Solution" in result.content


def test_export_course_pattern_and_interview_markdown(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock(id=session_id, title="Course", feature=AIFeature.COURSE_GENERATOR)
    messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="Course body",
            content_metadata={"structured": {"course": {"title": "Arrays 101", "modules": []}}},
            created_at=datetime.now(UTC),
        ),
    ]
    export = _service(session=session, messages=messages)
    course = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.COURSE),
    )
    assert "Learning Path" in course.content or "Course Export" in course.content

    pattern_session = MagicMock(id=session_id, title="Pattern", feature=AIFeature.DSA_PATTERN)
    pattern_messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="Pattern body",
            content_metadata={"structured": {"dsa_pattern": {"title": "Two Pointers", "steps": []}}},
            created_at=datetime.now(UTC),
        ),
    ]
    pattern_export = _service(session=pattern_session, messages=pattern_messages)
    pattern = pattern_export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.PATTERN),
    )
    assert "DSA Pattern" in pattern.content or "Pattern Export" in pattern.content

    interview_session = MagicMock(id=session_id, title="Interview", feature=AIFeature.INTERVIEW)
    interview_messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="Good answer",
            content_metadata={"structured": {"evaluator": {"score": 8}}},
            created_at=datetime.now(UTC),
        ),
    ]
    interview_export = _service(session=interview_session, messages=interview_messages)
    interview = interview_export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.INTERVIEW_REPORT),
    )
    assert "Interview Report" in interview.content


def test_export_structured_pdf_and_txt(monkeypatch, user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock(id=session_id, title="Two Sum", feature=AIFeature.LEETCODE)
    messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="Explanation",
            content_metadata={"structured": {"teacher": {"explanation": "done"}}},
            created_at=datetime.now(UTC),
        ),
    ]
    export = _service(session=session, messages=messages)
    monkeypatch.setattr(
        "app.agents.course_generator.adapter.markdown_to_simple_pdf",
        lambda markdown, *, title: b"%PDF-fake",
    )
    pdf = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.PDF, export_type=ExportType.SOLUTION),
    )
    assert pdf.format == ExportFormat.PDF
    txt = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.TXT, export_type=ExportType.SOLUTION),
    )
    assert txt.content_type == "text/plain"


def test_export_extract_structured_from_memory_and_teacher_responses(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock(id=session_id, title="Memory", feature=AIFeature.LEETCODE)
    detail = SessionDetailResponse(
        session=SessionSummaryResponse(
            id=session_id,
            feature=AIFeature.LEETCODE,
            title="Memory",
            status=SessionStatus.COMPLETED,
            summary=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        messages=[],
        total_messages=0,
        memory=ConversationMemoryResponse(
            session_id=session_id,
            summary=None,
            context={"teacher": {"explanation": "from memory"}},
            recent_messages=[],
            previous_responses=[],
            follow_up_questions=[],
            memory_version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    )
    export = _service(session=session, messages=[], detail=detail)
    result = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.JSON, export_type=ExportType.SOLUTION),
    )
    assert "teacher" in json.loads(result.content)


def test_export_course_and_pattern_fallback_json(monkeypatch, user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock(id=session_id, title="Broken", feature=AIFeature.COURSE_GENERATOR)
    messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="bad",
            content_metadata={"structured": {"course": {"invalid": True}}},
            created_at=datetime.now(UTC),
        ),
    ]
    export = _service(session=session, messages=messages)
    course = export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.COURSE),
    )
    assert "Learning Path" in course.content or "Course Export" in course.content or "```json" in course.content

    pattern_session = MagicMock(id=session_id, title="Broken Pattern", feature=AIFeature.DSA_PATTERN)
    pattern_messages = [
        MessageResponse(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            module_name=ModuleName.TEACHER,
            content="bad",
            content_metadata={"structured": {"dsa_pattern": {"invalid": True}}},
            created_at=datetime.now(UTC),
        ),
    ]
    pattern_export = _service(session=pattern_session, messages=pattern_messages)
    pattern = pattern_export.export_session(
        user,
        ChatExportRequest(session_id=session_id, format=ExportFormat.MARKDOWN, export_type=ExportType.PATTERN),
    )
    assert "Pattern Export" in pattern.content or "DSA Pattern" in pattern.content or "```json" in pattern.content
