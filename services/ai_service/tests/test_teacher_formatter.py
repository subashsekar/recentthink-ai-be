"""Teacher formatter unit tests."""

from __future__ import annotations

from app.agents.shared.teacher.formatter import TeacherFormatter
from app.agents.shared.teacher.schemas import TeacherOutput


def test_teacher_output_from_payload_maps_mistakes() -> None:
    output = TeacherOutput.from_payload(
        {
            "problem_summary": "Two Sum",
            "common_mistakes": ["Nested loops"],
            "next_step": "Think about complements.",
        },
    )
    assert output.problem_summary == "Two Sum"
    assert output.common_mistakes == ["Nested loops"]
    assert output.next_step == "Think about complements."


def test_teacher_output_to_cards() -> None:
    output = TeacherOutput(
        problem_summary="Find two numbers.",
        concepts=["Hash Map"],
        analogy="Like finding a matching sock.",
        next_step="Try hashing complements.",
    )
    cards = output.to_cards()
    ids = {card.id for card in cards}
    assert "problem_summary" in ids
    assert "concepts" in ids
    assert "analogy" in ids
    assert "next_step" in ids


def test_teacher_formatter_produces_markdown() -> None:
    formatter = TeacherFormatter()
    output = TeacherOutput(
        thinking_process="Break down the array.",
        approach="Use a hash map.",
        common_mistakes=["O(n^2) brute force"],
    )
    markdown, cards = formatter.format(output)
    assert "Thinking Process" in markdown
    assert "Approach" in markdown
    assert "Common Beginner Mistakes" in markdown
    assert len(cards) >= 3
