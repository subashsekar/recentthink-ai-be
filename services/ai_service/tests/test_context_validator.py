"""Context detection tests for follow-up relevance gating."""

from __future__ import annotations

import pytest
from app.agents.shared.followup.context_validator import ContextValidator
from app.models.enums import AIFeature


@pytest.fixture
def validator() -> ContextValidator:
    return ContextValidator()


@pytest.mark.parametrize(
    ("question", "feature", "context"),
    [
        ("Explain why HashMap works.", AIFeature.LEETCODE, {"title": "Two Sum", "description": "Use a hash map"}),
        ("Can recursion solve this?", AIFeature.LEETCODE, {"title": "Climbing Stairs"}),
        ("Show C++ solution.", AIFeature.LEETCODE, {"title": "Two Sum"}),
        ("Explain the SQL query.", AIFeature.HACKERRANK, {"title": "Weather Observation", "domain": "SQL"}),
        ("Optimize this algorithm.", AIFeature.HACKERRANK, {"title": "Sorting", "description": "algorithm"}),
        ("Explain Sliding Window again.", AIFeature.DSA_PATTERN, {"pattern": "Sliding Window"}),
        ("Give me another practice problem.", AIFeature.DSA_PATTERN, {"pattern": "Two Pointers"}),
        ("Expand Lesson 5.", AIFeature.COURSE_GENERATOR, {"skill": "Python", "goal": "Backend"}),
        ("Generate another project.", AIFeature.COURSE_GENERATOR, {"skill": "Django"}),
    ],
)
def test_accepts_in_context_questions(
    validator: ContextValidator,
    question: str,
    feature: AIFeature,
    context: dict,
) -> None:
    result = validator.validate(question=question, feature=feature, session_context=context)
    assert validator.is_accepted(result)
    assert result.in_context is True


@pytest.mark.parametrize(
    ("question", "feature"),
    [
        ("Who is Elon Musk?", AIFeature.LEETCODE),
        ("Who won the FIFA World Cup?", AIFeature.LEETCODE),
        ("Write a leave application.", AIFeature.HACKERRANK),
        ("Tell me today's weather.", AIFeature.HACKERRANK),
        ("Teach me React.", AIFeature.DSA_PATTERN),
        ("Tell me a joke.", AIFeature.COURSE_GENERATOR),
        ("What is IPL?", AIFeature.LEETCODE),
        ("Explain Kubernetes.", AIFeature.DSA_PATTERN),
    ],
)
def test_rejects_out_of_context_questions(
    validator: ContextValidator,
    question: str,
    feature: AIFeature,
) -> None:
    result = validator.validate(
        question=question,
        feature=feature,
        session_context={"title": "Two Sum", "pattern": "Hash Map", "skill": "Python"},
    )
    assert validator.is_accepted(result) is False
    assert result.rejection_message is not None
    assert "session" in result.rejection_message.lower()


def test_course_allows_topic_overlap_for_aws(validator: ContextValidator) -> None:
    result = validator.validate(
        question="Explain AWS pricing for this course module.",
        feature=AIFeature.COURSE_GENERATOR,
        session_context={
            "skill": "AWS Cloud Practitioner",
            "goal": "Understand AWS pricing and billing",
            "topics_include": ["AWS", "pricing", "EC2"],
        },
    )
    assert validator.is_accepted(result) is True


def test_rejection_message_is_feature_specific(validator: ContextValidator) -> None:
    leetcode_msg = ContextValidator.build_rejection_message(AIFeature.LEETCODE)
    pattern_msg = ContextValidator.build_rejection_message(AIFeature.DSA_PATTERN)
    assert "LeetCode" in leetcode_msg
    assert "DSA Pattern Coach" in pattern_msg
    assert leetcode_msg != pattern_msg


def test_low_confidence_is_rejected(validator: ContextValidator) -> None:
    result = validator.validate(
        question="Please discuss medieval architecture history books.",
        feature=AIFeature.LEETCODE,
        session_context={"title": "Two Sum"},
    )
    assert validator.is_accepted(result) is False


def test_deictic_short_question_accepted(validator: ContextValidator) -> None:
    result = validator.validate(
        question="Explain this again?",
        feature=AIFeature.LEETCODE,
        session_context={"title": "Two Sum"},
    )
    # Pedagogical pattern wins; still in context.
    assert validator.is_accepted(result) is True


def test_session_token_overlap_accepts_title_reference(validator: ContextValidator) -> None:
    result = validator.validate(
        question="How does two sum relate to complements?",
        feature=AIFeature.LEETCODE,
        session_context={"title": "Two Sum", "description": "complements in a hash map"},
    )
    assert validator.is_accepted(result) is True


def test_memory_nested_problem_used_for_anchors(validator: ContextValidator) -> None:
    result = validator.validate(
        question="Walk through the climbing stairs dp table.",
        feature=AIFeature.LEETCODE,
        session_context=None,
        memory_context={
            "context": {
                "problem": {
                    "title": "Climbing Stairs",
                    "description": "dynamic programming dp table",
                }
            }
        },
    )
    assert validator.is_accepted(result) is True
