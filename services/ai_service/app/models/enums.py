"""AI service domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class SessionStatus(StrEnum):
    """Lifecycle status of an AI session."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


class AIFeature(StrEnum):
    """Supported AI product features."""

    LEETCODE = "leetcode"
    HACKERRANK = "hackerrank"
    DSA = "dsa"
    INTERVIEW = "interview"
    COURSE_GENERATOR = "course_generator"


class ExecutionMode(StrEnum):
    """How the platform executes an AI request."""

    SINGLE_LLM = "single_llm"


class ModuleName(StrEnum):
    """Processing modules in the AI pipeline."""

    PLANNER = "planner"
    LLM = "llm"
    OPENROUTER = "openrouter"
    TEACHER = "teacher"
    CODER = "coder"
    EVALUATOR = "evaluator"
    PERSIST = "persist"


class WorkflowStatus(StrEnum):
    """Lifecycle status of a LangGraph workflow execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentName(StrEnum):
    """Backward-compatible identifiers for pipeline participants."""

    PLANNER = "planner"
    TEACHER = "teacher"
    CODER = "coder"
    EVALUATOR = "evaluator"


class AgentRunStatus(StrEnum):
    """Outcome of a single module execution."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class MessageRole(StrEnum):
    """Chat message role for conversation storage."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
