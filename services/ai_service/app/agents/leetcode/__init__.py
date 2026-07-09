"""LeetCode reference adapter — thin wrapper over the shared AI platform."""

from app.agents.leetcode.agents import (
    LEETCODE_AGENT_SPECS,
    LEETCODE_FEATURE,
    LEETCODE_OPENROUTER_PROMPT,
    LeetCodeAgentRole,
    LeetCodeAgentSpec,
    LeetCodeAgents,
)

__all__ = [
    "LEETCODE_AGENT_SPECS",
    "LEETCODE_FEATURE",
    "LEETCODE_OPENROUTER_PROMPT",
    "LeetCodeAgentRole",
    "LeetCodeAgentSpec",
    "LeetCodeAgents",
]
