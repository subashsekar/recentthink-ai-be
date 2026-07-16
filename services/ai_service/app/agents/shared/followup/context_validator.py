"""Lightweight in-session context validation for follow-up questions.

No LLM calls — keyword overlap + pedagogical heuristics only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.models.enums import AIFeature

# High-confidence off-topic patterns (reject unless strong session overlap).
_OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(elon\s*musk|who\s+is\s+\w+|celebrities?|taylor\s+swift|"
        r"who\s+won|fifa|world\s*cup|ipl|cricket|football\s+match|"
        r"today'?s?\s+weather|weather\s+forecast|tell\s+me\s+a\s+joke|"
        r"leave\s+application|resignation\s+letter|write\s+a\s+poem|"
        r"love\s+letter|horoscope|stock\s+tips?|crypto\s+price)\b",
        re.I,
    ),
    re.compile(
        r"\b(kubernetes|k8s|docker\s+swarm|aws\s+pricing|azure\s+billing|"
        r"react\s+native|teach\s+me\s+react|angular\s+tutorial|"
        r"machine\s+learning\s+interview(?!\s+prep))\b",
        re.I,
    ),
)

# Pedogical / learning follow-ups that belong inside a product session.
_IN_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(explain|again|slower|simpler|simplify|analogy|example|"
        r"edge\s*cases?|complexity|big\s*o|optimize|optimisation|optimization|"
        r"memory|space|time\s+complexity|solution|code|approach|"
        r"recursion|hash\s*map|hashmap|array|tree|graph|dp|dynamic|"
        r"sliding\s+window|two\s+pointers?|binary\s+search|"
        r"quiz|assignment|lesson|project|practice|roadmap|template|"
        r"visualization|visualise|visualize|pattern|challenge|"
        r"sql|query|algorithm|pseudocode|walk\s*through|hint|"
        r"java|python|c\+\+|javascript|typescript|golang|rust|csharp|"
        r"show\s+me|give\s+me|another|expand|compare|clarify|"
        r"didn'?t\s+understand|confused|why\s+does|how\s+does|"
        r"test\s+case|brute\s+force|interview\s+tip)\b",
        re.I,
    ),
)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "but",
        "with",
        "this",
        "that",
        "it",
        "my",
        "me",
        "i",
        "you",
        "your",
        "can",
        "please",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "do",
        "does",
        "did",
        "about",
        "just",
        "more",
        "some",
        "any",
        "from",
        "into",
        "also",
        "very",
        "really",
        "tell",
        "give",
        "show",
        "make",
        "want",
        "need",
        "help",
        "thanks",
        "thank",
    }
)

_FEATURE_LABELS: dict[str, tuple[str, str]] = {
    AIFeature.LEETCODE.value: ("LeetCode", "this problem"),
    AIFeature.HACKERRANK.value: ("HackerRank", "this challenge"),
    AIFeature.DSA_PATTERN.value: ("DSA Pattern Coach", "this pattern"),
    AIFeature.COURSE_GENERATOR.value: ("Course Generator", "this course"),
    AIFeature.DSA.value: ("DSA Tutor", "this topic"),
    AIFeature.INTERVIEW.value: ("Interview Trainer", "this interview session"),
}

# Minimum confidence to proceed with an OpenRouter call.
_ACCEPT_CONFIDENCE = 0.55


@dataclass(frozen=True)
class ContextValidationResult:
    """Result of inexpensive session-context relevance checks."""

    in_context: bool
    confidence: float
    reason: str
    rejection_message: str | None = None


class ContextValidator:
    """Decide whether a follow-up belongs to the current learning session."""

    def validate(
        self,
        *,
        question: str,
        feature: str | AIFeature,
        session_context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
    ) -> ContextValidationResult:
        feature_key = feature.value if isinstance(feature, AIFeature) else str(feature)
        anchors = self._extract_anchors(session_context, memory_context)
        q = (question or "").strip()
        q_lower = q.lower()
        overlap = self._overlap_score(q_lower, anchors)
        off_topic = self._matches_any(q, _OFF_TOPIC_PATTERNS)
        pedagogical = self._matches_any(q, _IN_CONTEXT_PATTERNS)

        # Strong off-topic with little/no session overlap → reject without LLM.
        if off_topic and overlap < 0.25:
            return ContextValidationResult(
                in_context=False,
                confidence=0.95,
                reason="off_topic_pattern",
                rejection_message=self.build_rejection_message(feature_key),
            )

        # Off-topic keywords but clear overlap with session topic (e.g. AWS in course).
        if off_topic and overlap >= 0.25:
            return ContextValidationResult(
                in_context=True,
                confidence=min(0.9, 0.55 + overlap),
                reason="off_topic_but_session_overlap",
            )

        if pedagogical:
            return ContextValidationResult(
                in_context=True,
                confidence=max(0.75, 0.6 + overlap * 0.4),
                reason="pedagogical_follow_up",
            )

        if overlap >= 0.35:
            return ContextValidationResult(
                in_context=True,
                confidence=min(0.92, 0.5 + overlap),
                reason="session_token_overlap",
            )

        # Short vague questions about "this" / prior answer stay in-session.
        if len(q.split()) <= 8 and re.search(
            r"\b(this|that|previous|above|same|here|it)\b",
            q_lower,
        ):
            return ContextValidationResult(
                in_context=True,
                confidence=0.7,
                reason="session_deictic_reference",
            )

        if overlap < 0.15 and len(q.split()) >= 3:
            return ContextValidationResult(
                in_context=False,
                confidence=0.8,
                reason="low_context_overlap",
                rejection_message=self.build_rejection_message(feature_key),
            )

        # Low confidence → reject (never become a generic chatbot).
        return ContextValidationResult(
            in_context=False,
            confidence=0.4 + overlap,
            reason="low_confidence",
            rejection_message=self.build_rejection_message(feature_key),
        )

    def is_accepted(self, result: ContextValidationResult) -> bool:
        return result.in_context and result.confidence >= _ACCEPT_CONFIDENCE

    @staticmethod
    def build_rejection_message(feature: str | AIFeature) -> str:
        feature_key = feature.value if isinstance(feature, AIFeature) else str(feature)
        product, focus = _FEATURE_LABELS.get(feature_key, ("RecentThink", "this learning session"))
        return (
            f"This conversation is dedicated to your current {product} session.\n\n"
            f"Please ask questions related to {focus}.\n\n"
            "If you want to explore another topic, open the appropriate AI product "
            "or start a new session."
        )

    @staticmethod
    def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    def _extract_anchors(
        self,
        session_context: dict[str, Any] | None,
        memory_context: dict[str, Any] | None,
    ) -> set[str]:
        blobs: list[str] = []
        for source in (session_context, memory_context):
            if isinstance(source, dict):
                blobs.append(self._flatten_context(source))
        nested = (memory_context or {}).get("context") if isinstance(memory_context, dict) else None
        if isinstance(nested, dict):
            blobs.append(self._flatten_context(nested))
            problem = nested.get("problem")
            if isinstance(problem, dict):
                blobs.append(self._flatten_context(problem))
        tokens: set[str] = set()
        for blob in blobs:
            tokens.update(self._tokenize(blob))
        return tokens

    def _flatten_context(self, data: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in (
            "title",
            "description",
            "pattern",
            "pattern_name",
            "skill",
            "goal",
            "domain",
            "category",
            "difficulty",
            "summary",
            "name",
            "topic",
            "challenge_slug",
            "problem_slug",
            "programming_language",
            "language",
        ):
            value = data.get(key)
            if value:
                parts.append(str(value))
        for key in ("topics", "topics_include", "patterns", "tags", "concepts"):
            value = data.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value if item)
            elif isinstance(value, str) and value:
                parts.append(value)
        teacher = data.get("teacher_output")
        if isinstance(teacher, dict):
            for key in ("problem_summary", "approach", "concepts", "explanation"):
                value = teacher.get(key)
                if isinstance(value, list):
                    parts.extend(str(item) for item in value[:8])
                elif value:
                    parts.append(str(value)[:400])
        return " ".join(parts)

    def _overlap_score(self, question: str, anchors: set[str]) -> float:
        if not anchors:
            # Without anchors, rely on pedagogical patterns only.
            return 0.0
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return 0.0
        hits = sum(1 for token in q_tokens if token in anchors or self._fuzzy_in(token, anchors))
        return hits / max(len(q_tokens), 1)

    @staticmethod
    def _fuzzy_in(token: str, anchors: set[str]) -> bool:
        if len(token) < 4:
            return False
        return any(token in anchor or anchor in token for anchor in anchors if len(anchor) >= 4)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        raw = re.findall(r"[a-z0-9\+#]+", text.lower())
        return {token for token in raw if token not in _STOPWORDS and len(token) > 1}
