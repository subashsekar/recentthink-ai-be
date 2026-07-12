"""Deterministic planner — no LLM calls."""

from __future__ import annotations

from typing import Any

from app.models.enums import AIFeature, ExecutionMode, ModuleName
from app.schemas.ai import ChatRequest, PlannerOutput
from shared.exceptions.base import ValidationException

_FEATURE_MODULES: dict[AIFeature, list[ModuleName]] = {
    AIFeature.LEETCODE: [ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
    AIFeature.HACKERRANK: [
        ModuleName.TEACHER,
        ModuleName.CODER,
        ModuleName.CODE_EXPLAINER,
        ModuleName.EVALUATOR,
    ],
    AIFeature.DSA: [ModuleName.TEACHER, ModuleName.EVALUATOR],
    AIFeature.DSA_PATTERN: [ModuleName.TEACHER],
    AIFeature.INTERVIEW: [ModuleName.TEACHER, ModuleName.EVALUATOR],
    AIFeature.COURSE_GENERATOR: [ModuleName.TEACHER],
}

_FEATURE_ALIASES: dict[str, AIFeature] = {
    "leetcode": AIFeature.LEETCODE,
    "hackerrank": AIFeature.HACKERRANK,
    "dsa": AIFeature.DSA,
    "dsa_tutor": AIFeature.DSA,
    "dsa_pattern": AIFeature.DSA_PATTERN,
    "dsa-pattern": AIFeature.DSA_PATTERN,
    "pattern_coach": AIFeature.DSA_PATTERN,
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

    def plan(self, request: ChatRequest, *, mode_id: str | None = None) -> PlannerOutput:
        self._validate_request(request)
        feature = self._resolve_feature(request)
        modules = list(_FEATURE_MODULES[feature])
        metadata = self._build_metadata(request, feature, mode_id=mode_id)
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

    def _build_metadata(self, request: ChatRequest, feature: AIFeature, *, mode_id: str | None) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "classification": self.classify_message(request.message),
            "has_session": request.session_id is not None,
            "has_context": bool(request.context),
            "requested_model": request.model,
            "feature": feature.value,
            "mode_id": mode_id,
        }
        if feature == AIFeature.LEETCODE and request.context:
            metadata.update(self._build_leetcode_metadata(request.context, mode_id=mode_id))
        if feature == AIFeature.HACKERRANK and request.context:
            metadata.update(self._build_hackerrank_metadata(request.context, mode_id=mode_id))
        if feature == AIFeature.COURSE_GENERATOR and request.context:
            metadata.update(self._build_course_generator_metadata(request.context, mode_id=mode_id))
        if feature == AIFeature.DSA_PATTERN and request.context:
            metadata.update(self._build_dsa_pattern_metadata(request.context, mode_id=mode_id))
        return metadata

    @classmethod
    def _build_leetcode_metadata(cls, context: dict[str, Any], *, mode_id: str | None) -> dict[str, Any]:
        topics = list(context.get("topics") or [])
        title = str(context.get("title") or "")
        description = str(context.get("description") or "")
        difficulty = str(context.get("difficulty") or "Unknown")
        patterns = topics or cls._detect_patterns(f"{title} {description}")
        category = topics[0] if topics else (patterns[0] if patterns else "General")
        plan = list(_LEETCODE_EXECUTION_PLAN)
        if mode_id == "quick":
            plan = ["Identify the optimal pattern", "Write clean optimal code", "State complexity"]
        elif mode_id == "interview":
            plan = [
                "Clarify inputs/outputs and constraints",
                "Describe approach and trade-offs",
                "Implement",
                "Analyze complexity",
                "Discuss edge cases and follow-ups",
            ]
        elif mode_id == "teacher":
            plan = [
                "Restate problem in your own words",
                "Identify key concept/pattern",
                "Plan and checkpoints",
                "Walk through an example",
                "Compare approaches",
                "Complexity + practice exercises",
            ]
        return {
            "problem_category": category,
            "difficulty": difficulty,
            "patterns": patterns,
            "execution_plan": plan,
            "problem_slug": context.get("slug"),
            "problem_url": context.get("url"),
            "learning_objectives": cls._learning_objectives(patterns),
        }

    @classmethod
    def _build_hackerrank_metadata(cls, context: dict[str, Any], *, mode_id: str | None) -> dict[str, Any]:
        title = str(context.get("title") or "")
        description = str(context.get("description") or "")
        difficulty = str(context.get("difficulty") or "Unknown")
        topics = list(context.get("topics") or context.get("tags") or [])
        detected = cls._detect_patterns(f"{title} {description}")
        patterns = topics or detected

        domain = str(context.get("domain") or context.get("problem_domain") or "")
        category = domain or (patterns[0] if patterns else "General")

        plan = [
            "Understand the problem statement and constraints",
            "Identify domain + core concepts (algorithms / data structures / SQL / regex)",
            "Design an approach and validate with examples",
            "Implement a clean solution in the chosen language",
            "Explain line-by-line and analyze complexity",
        ]
        if mode_id == "quick":
            plan = ["Identify the optimal approach", "Implement", "State complexity", "Explain key lines"]
        elif mode_id == "interview":
            plan = [
                "Clarify I/O and constraints",
                "Pick approach and trade-offs",
                "Implement",
                "Explain complexity and edge cases",
                "Discuss follow-ups and optimizations",
            ]
        elif mode_id == "teacher":
            plan = [
                "Restate the problem",
                "Identify the domain and learning objectives",
                "Walk through an example",
                "Build the solution incrementally",
                "Explain every important line",
                "Complexity + practice variations",
            ]

        learning_objectives = list(context.get("learning_objectives") or [])
        if not learning_objectives:
            learning_objectives = cls._learning_objectives(patterns)

        return {
            "problem_category": category,
            "difficulty": difficulty,
            "patterns": patterns,
            "execution_plan": plan,
            "problem_slug": context.get("slug"),
            "problem_url": context.get("url"),
            "problem_domain": domain or None,
            "topics": topics,
            "tags": list(context.get("tags") or []),
            "languages": list(context.get("languages") or []),
            "learning_objectives": learning_objectives,
        }

    @classmethod
    def _build_course_generator_metadata(cls, context: dict[str, Any], *, mode_id: str | None) -> dict[str, Any]:
        skill = str(context.get("skill") or "General")
        goal = str(context.get("goal") or context.get("target_role") or "")
        level = str(context.get("level") or context.get("current_level") or "Beginner")
        target_level = str(context.get("target_level") or "Advanced")
        duration_days = int(context.get("duration_days") or 60)
        daily_hours = float(context.get("daily_hours") or 2.0)
        learning_style = str(context.get("learning_style") or "Hands-on")
        programming_language = str(context.get("programming_language") or "Python")
        topics_include = list(context.get("topics_include") or [])
        topics_exclude = list(context.get("topics_exclude") or [])
        estimated_study_hours = round(duration_days * daily_hours, 1)
        weeks = max(1, duration_days // 7)

        plan = [
            "Analyze learner goal, level, and time budget",
            "Design week-wise roadmap with milestones",
            "Generate lessons, quizzes, assignments, and projects",
            "Add assessments, resources, and adaptive recommendations",
            "Produce a frontend-ready structured learning path",
        ]
        if mode_id == "quick":
            plan = ["Outline roadmap", "Generate core lessons", "Add one project and quiz set"]
        elif mode_id == "teacher":
            plan = [
                "Clarify prerequisites and learning objectives",
                "Build progressive week-wise curriculum",
                "Write concept explanations with analogies and examples",
                "Add practice (quizzes, assignments) and projects",
                "Include assessments and next-step recommendations",
            ]

        learning_objectives = [
            f"Build {skill} skills toward: {goal}" if goal else f"Build practical {skill} skills",
            f"Progress from {level} toward {target_level}",
            f"Complete a {duration_days}-day plan at ~{daily_hours}h/day ({estimated_study_hours}h total)",
        ]
        if topics_include:
            learning_objectives.append(f"Cover: {', '.join(topics_include[:5])}")

        roadmap_outline = [f"Week {i}: Core {skill} progression" for i in range(1, min(weeks, 8) + 1)]
        if weeks > 8:
            roadmap_outline.append(f"Weeks 9–{weeks}: Advanced topics, projects, and assessments")

        milestones = [
            f"Complete foundational {skill} concepts",
            "Finish mid-course project checkpoint",
            "Pass weekly assessments",
            "Ship a resume-ready capstone project",
        ]

        prerequisites = list(context.get("prerequisites") or [])
        if not prerequisites and level.lower() in {"beginner", "novice"}:
            prerequisites = [
                "Basic computer literacy",
                f"Willingness to practice {programming_language} daily",
            ]

        return {
            "skill": skill,
            "goal": goal,
            "difficulty": level,
            "current_level": level,
            "target_level": target_level,
            "duration_days": duration_days,
            "daily_hours": daily_hours,
            "estimated_study_hours": estimated_study_hours,
            "learning_style": learning_style,
            "language": context.get("language") or "English",
            "programming_language": programming_language,
            "topics_include": topics_include,
            "topics_exclude": topics_exclude,
            "learning_objectives": learning_objectives,
            "prerequisites": prerequisites,
            "roadmap_outline": roadmap_outline,
            "milestones": milestones,
            "execution_plan": plan,
            "weeks": weeks,
            "output_format": context.get("output_format") or "full",
        }

    @classmethod
    def _build_dsa_pattern_metadata(cls, context: dict[str, Any], *, mode_id: str | None) -> dict[str, Any]:
        pattern = str(context.get("pattern") or "General")
        level = str(context.get("level") or "Beginner")
        language = str(context.get("language") or "Python")
        learning_style = str(context.get("learning_style") or "Visual")
        detected = cls._detect_patterns(pattern)
        category = detected[0] if detected and detected[0] != "General" else pattern

        study_time_by_level = {
            "beginner": "4–6 hours",
            "intermediate": "6–10 hours",
            "advanced": "8–14 hours",
        }
        estimated_study_time = study_time_by_level.get(level.lower(), "6–10 hours")

        plan = [
            "Define the pattern and build a mental model",
            "Teach recognition keywords, signals, and decision rules",
            "Visualize the pattern with ASCII / step-by-step diagrams",
            "Provide reusable multi-language templates",
            "Walk through easy, medium, and hard examples",
            "Generate practice sets, quiz, interview tips, and next pattern",
        ]
        if mode_id == "quick":
            plan = [
                "Summarize pattern + recognition checklist",
                "Show one template and one worked example",
                "List practice problems and next pattern",
            ]
        elif mode_id == "teacher":
            plan = [
                "Explain why the pattern exists with analogies",
                "Drill recognition until the learner can spot it",
                "Visualize movement of pointers / state",
                "Compare with similar patterns",
                "Practice + quiz for mastery",
            ]

        learning_objectives = [
            f"Recognize when a problem belongs to {pattern}",
            f"Explain the {pattern} mental model in plain language",
            f"Apply a reusable {language} template for {pattern}",
            "Walk through easy/medium/hard examples with dry runs",
            "Compare this pattern with closely related alternatives",
        ]

        prerequisites = list(context.get("prerequisites") or [])
        if not prerequisites:
            if level.lower() in {"beginner", "novice"}:
                prerequisites = [
                    f"Basic {language} syntax",
                    "Arrays and loops",
                    "Big-O intuition (optional but helpful)",
                ]
            else:
                prerequisites = [
                    f"Comfortable with {language}",
                    "Core data structures (arrays, hash maps, stacks/queues)",
                    "Prior exposure to related easier patterns",
                ]

        roadmap = [
            f"Day 1: Overview + mental model for {pattern}",
            "Day 2: Recognition drills + visualization",
            "Day 3: Templates + easy walkthrough",
            "Day 4: Medium/hard walkthroughs + interview tips",
            "Day 5: Practice set + quiz + next pattern",
        ]

        return {
            "pattern": pattern,
            "category": category,
            "difficulty": level,
            "level": level,
            "language": language,
            "learning_style": learning_style,
            "estimated_study_time": estimated_study_time,
            "learning_objectives": learning_objectives,
            "prerequisites": prerequisites,
            "roadmap": roadmap,
            "roadmap_outline": roadmap,
            "execution_plan": plan,
            "patterns": [pattern],
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
