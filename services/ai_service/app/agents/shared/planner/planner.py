"""Deterministic planner — no LLM calls."""

from __future__ import annotations

from typing import Any

from app.models.enums import AIFeature, ExecutionMode, ModuleName
from app.schemas.ai import ChatRequest, PlannerOutput
from shared.exceptions.base import ValidationException

_FEATURE_MODULES: dict[AIFeature, list[ModuleName]] = {
    AIFeature.LEETCODE: [ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
    AIFeature.HACKERRANK: [ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
    AIFeature.DSA: [ModuleName.TEACHER, ModuleName.EVALUATOR],
    AIFeature.INTERVIEW: [ModuleName.TEACHER, ModuleName.EVALUATOR],
    AIFeature.COURSE_GENERATOR: [ModuleName.TEACHER],
}

_FEATURE_ALIASES: dict[str, AIFeature] = {
    "leetcode": AIFeature.LEETCODE,
    "hackerrank": AIFeature.HACKERRANK,
    "dsa": AIFeature.DSA,
    "dsa_tutor": AIFeature.DSA,
    "interview": AIFeature.INTERVIEW,
    "course_generator": AIFeature.COURSE_GENERATOR,
    "course-generator": AIFeature.COURSE_GENERATOR,
}

_LEETCODE_EXECUTION_PLAN = [
    "Understand the problem statement and constraints",
    "Identify the algorithmic pattern",
    "Design an approach before coding",
    "Implement and verify with examples",
    "Analyze time and space complexity",
]

_PATTERN_KEYWORDS: dict[str, list[str]] = {
    "Array": ["array", "subarray", "index", "two pointer"],
    "Hash Map": ["hash", "frequency", "count", "lookup"],
    "Binary Search": ["sorted", "binary search", "log n"],
    "Dynamic Programming": ["dp", "dynamic programming", "memo"],
    "Graph": ["graph", "node", "edge", "bfs", "dfs"],
    "Tree": ["tree", "binary tree", "root", "leaf"],
    "Stack": ["stack", "monotonic"],
    "Queue": ["queue", "deque"],
    "Greedy": ["greedy", "interval"],
    "Sliding Window": ["window", "substring"],
}


class Planner:
    """Validates requests and prepares execution metadata deterministically."""

    def plan(self, request: ChatRequest) -> PlannerOutput:
        self._validate_request(request)
        feature = self._resolve_feature(request)
        modules = list(_FEATURE_MODULES[feature])
        metadata = self._build_metadata(request, feature)
        return PlannerOutput(
            feature=feature,
            modules=modules,
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata=metadata,
        )

    @staticmethod
    def _validate_request(request: ChatRequest) -> None:
        if not request.message.strip():
            raise ValidationException("Message must not be empty.")
        if len(request.message) > 32000:
            raise ValidationException("Message exceeds maximum allowed length.")

    @staticmethod
    def _resolve_feature(request: ChatRequest) -> AIFeature:
        return request.feature

    @staticmethod
    def classify_message(message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ("code", "solution", "implement", "algorithm")):
            return "coding"
        if any(word in lowered for word in ("explain", "concept", "understand", "learn")):
            return "teaching"
        if any(word in lowered for word in ("complexity", "optimize", "interview")):
            return "evaluation"
        return "general"

    def _build_metadata(self, request: ChatRequest, feature: AIFeature) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "classification": self.classify_message(request.message),
            "has_session": request.session_id is not None,
            "has_context": bool(request.context),
            "requested_model": request.model,
            "feature": feature.value,
        }
        if feature == AIFeature.LEETCODE and request.context:
            metadata.update(self._build_leetcode_metadata(request.context))
        return metadata

    @classmethod
    def _build_leetcode_metadata(cls, context: dict[str, Any]) -> dict[str, Any]:
        topics = list(context.get("topics") or [])
        title = str(context.get("title") or "")
        description = str(context.get("description") or "")
        difficulty = str(context.get("difficulty") or "Unknown")
        patterns = topics or cls._detect_patterns(f"{title} {description}")
        category = topics[0] if topics else (patterns[0] if patterns else "General")
        return {
            "problem_category": category,
            "difficulty": difficulty,
            "patterns": patterns,
            "execution_plan": list(_LEETCODE_EXECUTION_PLAN),
            "problem_slug": context.get("slug"),
            "problem_url": context.get("url"),
            "learning_objectives": cls._learning_objectives(patterns),
        }

    @staticmethod
    def _detect_patterns(text: str) -> list[str]:
        lowered = text.lower()
        detected = [
            pattern
            for pattern, keywords in _PATTERN_KEYWORDS.items()
            if any(keyword in lowered for keyword in keywords)
        ]
        return detected or ["General"]

    @staticmethod
    def _learning_objectives(patterns: list[str]) -> list[str]:
        objectives = [f"Recognize when to apply {pattern}" for pattern in patterns[:3]]
        objectives.append("Explain time and space complexity trade-offs")
        return objectives

    @classmethod
    def resolve_feature_alias(cls, value: str) -> AIFeature:
        normalized = value.strip().lower()
        if normalized in _FEATURE_ALIASES:
            return _FEATURE_ALIASES[normalized]
        return AIFeature(normalized)
