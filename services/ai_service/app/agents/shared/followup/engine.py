"""Follow-up intent detection and handling."""

from __future__ import annotations

import re
from enum import StrEnum


class FollowUpIntent(StrEnum):
    """Recognized follow-up question types."""

    EXPLAIN_AGAIN = "explain_again"
    EXPLAIN_EASIER = "explain_easier"
    EXPLAIN_VISUALLY = "explain_visually"
    EXPLAIN_ANALOGY = "explain_analogy"
    ANOTHER_EXAMPLE = "another_example"
    SIMPLIFY = "simplify"
    EDGE_CASES = "edge_cases"
    DID_NOT_UNDERSTAND = "did_not_understand"
    GENERAL = "general"


_INTENT_PATTERNS: list[tuple[FollowUpIntent, re.Pattern[str]]] = [
    (FollowUpIntent.EXPLAIN_AGAIN, re.compile(r"\b(explain again|say that again|repeat)\b", re.I)),
    (FollowUpIntent.EXPLAIN_EASIER, re.compile(r"\b(explain easier|simpler|in simple terms|dumb it down)\b", re.I)),
    (FollowUpIntent.EXPLAIN_VISUALLY, re.compile(r"\b(visually|diagram|draw|visualize|picture)\b", re.I)),
    (FollowUpIntent.EXPLAIN_ANALOGY, re.compile(r"\b(analogy|analogies|like a real|real.?world)\b", re.I)),
    (FollowUpIntent.ANOTHER_EXAMPLE, re.compile(r"\b(another example|more examples|give example|show example)\b", re.I)),
    (FollowUpIntent.SIMPLIFY, re.compile(r"\b(simplify|break it down|step by step)\b", re.I)),
    (FollowUpIntent.EDGE_CASES, re.compile(r"\b(edge case|edge cases|corner case|what if)\b", re.I)),
    (FollowUpIntent.DID_NOT_UNDERSTAND, re.compile(r"\b(didn.?t understand|don.?t understand|confused|lost)\b", re.I)),
]


class FollowUpEngine:
    """Classify follow-up questions and select the appropriate prompt module."""

    def classify(self, question: str) -> FollowUpIntent:
        for intent, pattern in _INTENT_PATTERNS:
            if pattern.search(question):
                return intent
        return FollowUpIntent.GENERAL

    def resolve_prompt_module(self, intent: FollowUpIntent) -> str:
        if intent == FollowUpIntent.EXPLAIN_ANALOGY:
            return "analogy"
        return "followup"

    def build_instructions(self, intent: FollowUpIntent) -> str:
        instructions = {
            FollowUpIntent.EXPLAIN_AGAIN: "Re-explain the same concept using different words. Do not reveal the full solution.",
            FollowUpIntent.EXPLAIN_EASIER: "Explain in simpler language suitable for a beginner. Use short sentences.",
            FollowUpIntent.EXPLAIN_VISUALLY: "Describe a visual or step-by-step mental model the student can picture.",
            FollowUpIntent.EXPLAIN_ANALOGY: "Use a real-world analogy to make the concept intuitive.",
            FollowUpIntent.ANOTHER_EXAMPLE: "Provide a different worked example without giving the complete solution.",
            FollowUpIntent.SIMPLIFY: "Break the explanation into smaller, digestible steps.",
            FollowUpIntent.EDGE_CASES: "Discuss relevant edge cases and how to handle them conceptually.",
            FollowUpIntent.DID_NOT_UNDERSTAND: "Identify what might be confusing and clarify patiently.",
            FollowUpIntent.GENERAL: "Answer the follow-up using prior session context. Stay in mentor mode.",
        }
        return instructions[intent]
