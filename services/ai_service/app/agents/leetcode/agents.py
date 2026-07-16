"""LeetCode pipeline agent declarations.

Six agents participate in every LeetCode analyze request:

1. **Problem Fetcher** — LeetCode-specific; runs before the shared workflow.
2. **Planner** — deterministic classification; no OpenRouter.
3. **Teacher** — formats structured JSON; no OpenRouter.
4. **Coder** — formats solutions; no OpenRouter.
5. **Code Explainer** — formats line-by-line explanations; no OpenRouter.
6. **Evaluator** — formats feedback; no OpenRouter.

OpenRouter is invoked exactly once inside :class:`AIWorkflowEngine` (shared).
These agents never make independent LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.agents.leetcode.problem_fetcher import LeetCodeProblemFetcher
from app.agents.shared.code_explainer.module import CodeExplainerModule
from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.models.enums import AIFeature, ModuleName


class LeetCodeAgentRole(StrEnum):
    """Named roles in the LeetCode analyze pipeline."""

    PROBLEM_FETCHER = "problem_fetcher"
    PLANNER = "planner"
    TEACHER = "teacher"
    CODER = "coder"
    CODE_EXPLAINER = "code_explainer"
    EVALUATOR = "evaluator"


@dataclass(frozen=True)
class LeetCodeAgentSpec:
    """Static declaration for a LeetCode pipeline agent."""

    role: LeetCodeAgentRole
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: ModuleName | None
    prompt_module: str | None
    shared_path: str


LEETCODE_AGENT_SPECS: tuple[LeetCodeAgentSpec, ...] = (
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.PROBLEM_FETCHER,
        name="Problem Fetcher",
        description="Validate URL, fetch LeetCode problem metadata, normalize context.",
        uses_openrouter=False,
        workflow_module=None,
        prompt_module=None,
        shared_path="app.agents.leetcode.problem_fetcher.LeetCodeProblemFetcher",
    ),
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.PLANNER,
        name="Planner",
        description="Deterministic classification, pattern detection, module selection.",
        uses_openrouter=False,
        workflow_module=ModuleName.PLANNER,
        prompt_module="planner",
        shared_path="app.agents.shared.planner.planner.Planner",
    ),
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.TEACHER,
        name="Teacher",
        description="Format mentor explanations from unified LLM JSON.",
        uses_openrouter=False,
        workflow_module=ModuleName.TEACHER,
        prompt_module="teacher",
        shared_path="app.agents.shared.teacher.module.TeacherModule",
    ),
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.CODER,
        name="Coder",
        description="Format brute-force, better, and optimal solutions.",
        uses_openrouter=False,
        workflow_module=ModuleName.CODER,
        prompt_module="coder",
        shared_path="app.agents.shared.coder.module.CoderModule",
    ),
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.CODE_EXPLAINER,
        name="Code Explainer",
        description="Explain code line-by-line for multiple audiences from structured JSON. No extra LLM call.",
        uses_openrouter=False,
        workflow_module=ModuleName.CODE_EXPLAINER,
        prompt_module=None,
        shared_path="app.agents.shared.code_explainer.module.CodeExplainerModule",
    ),
    LeetCodeAgentSpec(
        role=LeetCodeAgentRole.EVALUATOR,
        name="Evaluator",
        description="Format complexity analysis, mistakes, and interview follow-ups.",
        uses_openrouter=False,
        workflow_module=ModuleName.EVALUATOR,
        prompt_module="evaluator",
        shared_path="app.agents.shared.evaluator.module.EvaluatorModule",
    ),
)

LEETCODE_FEATURE = AIFeature.LEETCODE
LEETCODE_OPENROUTER_PROMPT = "master"


@dataclass
class LeetCodeAgents:
    """Wired instances of the six LeetCode pipeline agents."""

    problem_fetcher: LeetCodeProblemFetcher
    planner: Planner
    teacher: TeacherModule
    coder: CoderModule
    code_explainer: CodeExplainerModule
    evaluator: EvaluatorModule

    @classmethod
    def create_default(cls) -> LeetCodeAgents:
        """Construct the default LeetCode agent bundle."""
        return cls(
            problem_fetcher=LeetCodeProblemFetcher(),
            planner=Planner(),
            teacher=TeacherModule(),
            coder=CoderModule(),
            code_explainer=CodeExplainerModule(),
            evaluator=EvaluatorModule(),
        )

    def get(self, role: LeetCodeAgentRole) -> Any:
        """Return the wired instance for a pipeline role."""
        mapping: dict[LeetCodeAgentRole, Any] = {
            LeetCodeAgentRole.PROBLEM_FETCHER: self.problem_fetcher,
            LeetCodeAgentRole.PLANNER: self.planner,
            LeetCodeAgentRole.TEACHER: self.teacher,
            LeetCodeAgentRole.CODER: self.coder,
            LeetCodeAgentRole.CODE_EXPLAINER: self.code_explainer,
            LeetCodeAgentRole.EVALUATOR: self.evaluator,
        }
        return mapping[role]

    @staticmethod
    def list_specs() -> list[LeetCodeAgentSpec]:
        """Return static declarations for all six agents."""
        return list(LEETCODE_AGENT_SPECS)
