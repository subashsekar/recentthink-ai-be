"""Teacher module output schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TeacherCard(BaseModel):
    """Frontend card payload for a single teaching section."""

    id: str
    title: str
    content: str
    type: str = "text"


class TeacherOutput(BaseModel):
    """Structured teacher response — mentor-style, no full solution reveal."""

    problem_summary: str = ""
    thinking_process: str = ""
    concepts: list[str] = Field(default_factory=list)
    approach: str = ""
    common_mistakes: list[str] = Field(default_factory=list)
    analogy: str = ""
    next_step: str = ""
    explanation: str = ""
    hints: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> TeacherOutput:
        mistakes = payload.get("common_mistakes") or payload.get("mistakes") or []
        objectives = payload.get("learning_objectives") or []
        return cls(
            problem_summary=str(payload.get("problem_summary", "")),
            thinking_process=str(payload.get("thinking_process", "")),
            concepts=list(payload.get("concepts") or []),
            approach=str(payload.get("approach", "")),
            common_mistakes=list(mistakes),
            analogy=str(payload.get("analogy", "")),
            next_step=str(payload.get("next_step", "")),
            explanation=str(payload.get("explanation", "")),
            hints=list(payload.get("hints") or []),
            learning_objectives=list(objectives),
        )

    def to_cards(self) -> list[TeacherCard]:
        cards: list[TeacherCard] = []
        if self.problem_summary:
            cards.append(TeacherCard(id="problem_summary", title="Problem Summary", content=self.problem_summary))
        if self.thinking_process:
            cards.append(TeacherCard(id="thinking_process", title="Thinking Process", content=self.thinking_process))
        if self.learning_objectives:
            content = "\n".join(f"- {obj}" for obj in self.learning_objectives)
            cards.append(TeacherCard(id="learning_objectives", title="Learning Objectives", content=content, type="list"))
        if self.concepts:
            content = "\n".join(f"- {c}" for c in self.concepts)
            cards.append(TeacherCard(id="concepts", title="DSA Concepts", content=content, type="list"))
        if self.approach:
            cards.append(TeacherCard(id="approach", title="Approach", content=self.approach))
        if self.common_mistakes:
            content = "\n".join(f"- {m}" for m in self.common_mistakes)
            cards.append(TeacherCard(id="common_mistakes", title="Common Beginner Mistakes", content=content, type="list"))
        if self.analogy:
            cards.append(TeacherCard(id="analogy", title="Real World Analogy", content=self.analogy))
        if self.next_step:
            cards.append(TeacherCard(id="next_step", title="Recommended Next Step", content=self.next_step, type="action"))
        if self.explanation:
            cards.append(TeacherCard(id="explanation", title="Explanation", content=self.explanation))
        if self.hints:
            content = "\n".join(f"- {h}" for h in self.hints)
            cards.append(TeacherCard(id="hints", title="Hints", content=content, type="list"))
        return cards
