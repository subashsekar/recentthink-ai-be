"""Teacher response formatter — markdown and frontend cards."""

from __future__ import annotations

from app.agents.shared.teacher.schemas import TeacherCard, TeacherOutput


class TeacherFormatter:
    """Format structured teacher JSON into markdown and frontend cards."""

    def format(self, output: TeacherOutput) -> tuple[str, list[TeacherCard]]:
        markdown = self.to_markdown(output)
        cards = output.to_cards()
        return markdown, cards

    @staticmethod
    def to_markdown(output: TeacherOutput) -> str:
        sections: list[str] = []

        if output.problem_summary:
            sections.append(f"## Problem Summary\n\n{output.problem_summary}")

        if output.thinking_process:
            sections.append(f"### Thinking Process\n\n{output.thinking_process}")

        if output.learning_objectives:
            sections.append("### Learning Objectives\n")
            sections.extend(f"- {obj}" for obj in output.learning_objectives)

        if output.explanation:
            sections.append(output.explanation)

        if output.approach:
            sections.append(f"### Approach\n\n{output.approach}")

        if output.concepts:
            sections.append("### Key Concepts\n")
            sections.extend(f"- {concept}" for concept in output.concepts)

        if output.common_mistakes:
            sections.append("### Common Beginner Mistakes\n")
            sections.extend(f"- {mistake}" for mistake in output.common_mistakes)

        if output.analogy:
            sections.append(f"### Real World Analogy\n\n{output.analogy}")

        if output.hints:
            sections.append("### Hints\n")
            sections.extend(f"- {hint}" for hint in output.hints)

        if output.next_step:
            sections.append(f"### Recommended Next Step\n\n> {output.next_step}")

        return "\n\n".join(sections).strip() or "No teacher output available."
