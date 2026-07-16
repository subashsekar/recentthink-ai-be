"""Tests for LeetCode agent declarations."""

from __future__ import annotations

from app.agents.leetcode.agents import LEETCODE_AGENT_SPECS, LeetCodeAgentRole, LeetCodeAgents


def test_leetcode_declares_six_agents() -> None:
    assert len(LEETCODE_AGENT_SPECS) == 6
    roles = {spec.role for spec in LEETCODE_AGENT_SPECS}
    assert roles == {
        LeetCodeAgentRole.PROBLEM_FETCHER,
        LeetCodeAgentRole.PLANNER,
        LeetCodeAgentRole.TEACHER,
        LeetCodeAgentRole.CODER,
        LeetCodeAgentRole.CODE_EXPLAINER,
        LeetCodeAgentRole.EVALUATOR,
    }


def test_only_problem_fetcher_is_leetcode_specific() -> None:
    fetcher = next(s for s in LEETCODE_AGENT_SPECS if s.role == LeetCodeAgentRole.PROBLEM_FETCHER)
    assert "leetcode.problem_fetcher" in fetcher.shared_path


def test_processing_agents_do_not_call_openrouter() -> None:
    for spec in LEETCODE_AGENT_SPECS:
        assert spec.uses_openrouter is False


def test_leetcode_agents_bundle_wires_instances() -> None:
    agents = LeetCodeAgents.create_default()
    assert agents.get(LeetCodeAgentRole.PLANNER) is agents.planner
    assert agents.get(LeetCodeAgentRole.TEACHER) is agents.teacher
    assert agents.get(LeetCodeAgentRole.CODE_EXPLAINER) is agents.code_explainer
    assert agents.get(LeetCodeAgentRole.EVALUATOR) is agents.evaluator
