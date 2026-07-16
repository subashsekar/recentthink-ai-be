"""Follow-up engine unit tests."""

from __future__ import annotations

from app.agents.shared.followup.engine import FollowUpEngine, FollowUpIntent


def test_classify_explain_again() -> None:
    engine = FollowUpEngine()
    assert engine.classify("Can you explain again?") == FollowUpIntent.EXPLAIN_AGAIN


def test_classify_another_example() -> None:
    engine = FollowUpEngine()
    assert engine.classify("Give another example please") == FollowUpIntent.ANOTHER_EXAMPLE


def test_classify_edge_cases() -> None:
    engine = FollowUpEngine()
    assert engine.classify("What about edge cases?") == FollowUpIntent.EDGE_CASES


def test_classify_did_not_understand() -> None:
    engine = FollowUpEngine()
    assert engine.classify("I didn't understand that") == FollowUpIntent.DID_NOT_UNDERSTAND


def test_classify_show_solution() -> None:
    engine = FollowUpEngine()
    assert engine.classify("Show Python solution") == FollowUpIntent.SHOW_SOLUTION
    assert engine.classify("Show me the code") == FollowUpIntent.SHOW_SOLUTION


def test_classify_optimize() -> None:
    engine = FollowUpEngine()
    assert engine.classify("Optimize memory usage") == FollowUpIntent.OPTIMIZE


def test_classify_generate_practice() -> None:
    engine = FollowUpEngine()
    assert engine.classify("Generate another quiz") == FollowUpIntent.GENERATE_PRACTICE
    assert engine.classify("Expand lesson 3") == FollowUpIntent.GENERATE_PRACTICE


def test_resolve_prompt_module_analogy() -> None:
    engine = FollowUpEngine()
    assert engine.resolve_prompt_module(FollowUpIntent.EXPLAIN_ANALOGY) == "analogy"


def test_resolve_prompt_module_default() -> None:
    engine = FollowUpEngine()
    assert engine.resolve_prompt_module(FollowUpIntent.GENERAL) == "followup"


def test_build_instructions_not_empty() -> None:
    engine = FollowUpEngine()
    for intent in FollowUpIntent:
        assert engine.build_instructions(intent)
