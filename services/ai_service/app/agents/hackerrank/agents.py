"""HackerRank pipeline agent declarations (feature adapter over shared platform)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.agents.hackerrank.problem_fetcher import HackerrankProblemFetcher
from app.agents.shared.code_explainer.module import CodeExplainerModule
from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.models.enums import AIFeature, ModuleName


class HackerrankAgentRole(StrEnum):
    PROBLEM_FETCHER = "problem_fetcher"
    PLANNER = "planner"
    TEACHER = "teacher"
    CODER = "coder"
    CODE_EXPLAINER = "code_explainer"
    EVALUATOR = "evaluator"


@dataclass(frozen=True)
class HackerrankAgentSpec:
    role: HackerrankAgentRole
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: ModuleName | None
    prompt_module: str | None
    shared_path: str


HACKERRANK_AGENT_SPECS: tuple[HackerrankAgentSpec, ...] = (
    HackerrankAgentSpec(
        role=HackerrankAgentRole.PROBLEM_FETCHER,
        name="Problem Fetcher",
        description="Validate URL, extract slug, best-effort fetch/normalize HackerRank challenge metadata.",
        uses_openrouter=False,
        workflow_module=None,
        prompt_module=None,
        shared_path="app.agents.hackerrank.problem_fetcher.HackerrankProblemFetcher",
    ),
    HackerrankAgentSpec(
        role=HackerrankAgentRole.PLANNER,
        name="Planner",
        description="Deterministic classification + HackerRank metadata enrichment.",
        uses_openrouter=False,
        workflow_module=ModuleName.PLANNER,
        prompt_module="planner",
        shared_path="app.agents.shared.planner.planner.Planner",
    ),
    HackerrankAgentSpec(
        role=HackerrankAgentRole.TEACHER,
        name="Teacher",
        description="Format mentor explanations from unified LLM JSON.",
        uses_openrouter=False,
        workflow_module=ModuleName.TEACHER,
        prompt_module="teacher",
        shared_path="app.agents.shared.teacher.module.TeacherModule",
    ),
    HackerrankAgentSpec(
        role=HackerrankAgentRole.CODER,
        name="Coder",
        description="Format brute-force, better, and optimal solutions.",
        uses_openrouter=False,
        workflow_module=ModuleName.CODER,
        prompt_module="coder",
        shared_path="app.agents.shared.coder.module.CoderModule",
    ),
    HackerrankAgentSpec(
        role=HackerrankAgentRole.CODE_EXPLAINER,
        name="Code Explainer",
        description="Explain code line-by-line for multiple audiences from structured JSON. No extra LLM call.",
        uses_openrouter=False,
        workflow_module=ModuleName.CODE_EXPLAINER,
        prompt_module=None,
        shared_path="app.agents.shared.code_explainer.module.CodeExplainerModule",
    ),
    HackerrankAgentSpec(
        role=HackerrankAgentRole.EVALUATOR,
        name="Evaluator",
        description="Format complexity analysis, mistakes, and interview follow-ups.",
        uses_openrouter=False,
        workflow_module=ModuleName.EVALUATOR,
        prompt_module="evaluator",
        shared_path="app.agents.shared.evaluator.module.EvaluatorModule",
    ),
)


@dataclass
class HackerrankAgents:
    problem_fetcher: HackerrankProblemFetcher
    planner: Planner
    teacher: TeacherModule
    coder: CoderModule
    code_explainer: CodeExplainerModule
    evaluator: EvaluatorModule

    @classmethod
    def create_default(cls) -> HackerrankAgents:
        return cls(
            problem_fetcher=HackerrankProblemFetcher(),
            planner=Planner(),
            teacher=TeacherModule(),
            coder=CoderModule(),
            code_explainer=CodeExplainerModule(),
            evaluator=EvaluatorModule(),
        )

    def get(self, role: HackerrankAgentRole) -> Any:
        mapping: dict[HackerrankAgentRole, Any] = {
            HackerrankAgentRole.PROBLEM_FETCHER: self.problem_fetcher,
            HackerrankAgentRole.PLANNER: self.planner,
            HackerrankAgentRole.TEACHER: self.teacher,
            HackerrankAgentRole.CODER: self.coder,
            HackerrankAgentRole.CODE_EXPLAINER: self.code_explainer,
            HackerrankAgentRole.EVALUATOR: self.evaluator,
        }
        return mapping[role]

    @staticmethod
    def list_specs() -> list[HackerrankAgentSpec]:
        return list(HACKERRANK_AGENT_SPECS)


HACKERRANK_FEATURE = AIFeature.HACKERRANK
HACKERRANK_OPENROUTER_PROMPT = "master"

