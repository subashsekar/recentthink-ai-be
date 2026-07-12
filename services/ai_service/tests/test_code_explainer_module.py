"""Unit tests for the Code Explainer processing module."""

from __future__ import annotations

from uuid import uuid4

from app.agents.shared.code_explainer.module import CodeExplainerModule
from app.models.enums import ModuleName


def test_code_explainer_derives_from_coder_payload() -> None:
    module = CodeExplainerModule()
    session_id = uuid4()
    payload = {
        "llm_raw": {
            "coder": {
                "optimal_solution": {"language": "python", "code": "def add(a,b):\n    return a+b\n"},
            },
            "evaluator": {"time_complexity": "O(1)", "space_complexity": "O(1)"},
        },
        "coder_output": {},
        "evaluator_output": {},
        "planner_output": {},
    }
    response = module.process(session_id=session_id, payload=payload, message_repo=None)
    assert response.module == ModuleName.CODE_EXPLAINER
    assert "Code Explanation" in response.content
    structured = response.structured or {}
    assert structured["solutions"][0]["language"] == "python"
    assert structured["solutions"][0]["beginner"]["lines"][0]["line_no"] == 1

