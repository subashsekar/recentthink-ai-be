"""Assistant message metadata helper tests."""

from __future__ import annotations

from app.schemas.ai import ChatResponse, ModuleResponse, PlannerOutput
from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.services.chat.message_metadata import (
    build_assistant_metadata,
    compute_missing_sections,
    expected_sections_from_planner,
    is_truncated_finish_reason,
    resolve_message_status,
    section_has_content,
    should_hide_message,
)
from uuid import uuid4


def _response() -> ChatResponse:
    return ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlannerOutput(feature=AIFeature.LEETCODE, modules=[ModuleName.TEACHER], execution_mode="single_llm"),
        modules=[
            ModuleResponse(
                module=ModuleName.TEACHER,
                content="Explain arrays",
                structured={"teacher": {"explanation": "Use hash map"}},
            ),
        ],
        model="openai/gpt-4o-mini",
        provider="openai",
        input_tokens=12,
        output_tokens=34,
        total_tokens=46,
        latency_ms=90,
        execution_time_ms=120,
        section_tokens={"teacher": 34},
    )


def test_is_truncated_finish_reason() -> None:
    assert is_truncated_finish_reason("length")
    assert is_truncated_finish_reason("MAX_TOKENS")
    assert not is_truncated_finish_reason("stop")
    assert not is_truncated_finish_reason(None)


def test_section_has_content_nested_and_empty() -> None:
    assert section_has_content({"teacher": {"explanation": "x"}}, "teacher")
    assert not section_has_content({"teacher": {}}, "teacher")
    assert not section_has_content({"teacher": "   "}, "teacher")
    assert section_has_content({"course": {"overview": "intro"}}, "overview")
    assert section_has_content({"overview": "x"}, "overview")


def test_compute_missing_sections() -> None:
    missing = compute_missing_sections(
        expected_sections=["teacher", "coder"],
        llm_raw={"teacher": {"explanation": "done"}},
    )
    assert missing == ["coder"]
    assert compute_missing_sections(expected_sections=None, llm_raw={}) is None
    assert compute_missing_sections(expected_sections=["teacher"], llm_raw={"teacher": {"x": 1}}) is None


def test_resolve_message_status() -> None:
    assert resolve_message_status(finish_reason="stop", missing_sections=None) == "completed"
    assert resolve_message_status(finish_reason="length", missing_sections=None) == "truncated"
    assert resolve_message_status(finish_reason="stop", missing_sections=["coder"]) == "truncated"
    assert resolve_message_status(finish_reason=None, missing_sections=None, errors=["boom"]) == "failed"


def test_build_assistant_metadata_includes_fields() -> None:
    metadata = build_assistant_metadata(
        _response(),
        action="stream",
        status="completed",
        finish_reason="stop",
        missing_sections=None,
        requested_sections=["teacher"],
        cache_hit=True,
        retry_count=1,
        generation_type="stream",
        prior_message_id="prior-id",
    )
    assert metadata["model"] == "openai/gpt-4o-mini"
    assert metadata["provider"] == "openai"
    assert metadata["prompt_tokens"] == 12
    assert metadata["completion_tokens"] == 34
    assert metadata["total_tokens"] == 46
    assert metadata["execution_time_ms"] == 120
    assert metadata["cache_hit"] is True
    assert metadata["retry_count"] == 1
    assert metadata["generation_type"] == "stream"
    assert metadata["structured"]["teacher"]["explanation"] == "Use hash map"
    assert metadata["supersedes_message_id"] == "prior-id"


def test_expected_sections_from_planner() -> None:
    assert expected_sections_from_planner(["teacher", "coder", "evaluator"]) == [
        "teacher",
        "coder",
        "evaluator",
    ]
    assert expected_sections_from_planner(["nested_only"]) is None


def test_should_hide_message() -> None:
    assert should_hide_message({"deleted": True}, include_hidden=False)
    assert should_hide_message({"status": "superseded"}, include_hidden=False)
    assert should_hide_message({"status": "failed"}, include_hidden=False)
    assert not should_hide_message({"status": "completed"}, include_hidden=False)
    assert not should_hide_message({"status": "failed"}, include_hidden=True)
