"""DSA Pattern Coach catalog helpers (example pattern cards)."""

from __future__ import annotations

from app.agents.dsa_pattern.schemas import PatternExampleResponse


def list_examples() -> list[PatternExampleResponse]:
    return [
        PatternExampleResponse(
            id="sliding-window",
            title="Sliding Window",
            pattern="Sliding Window",
            level="Beginner",
            language="Python",
            learning_style="Visual",
            icon="window",
        ),
        PatternExampleResponse(
            id="dynamic-programming",
            title="Dynamic Programming",
            pattern="Dynamic Programming",
            level="Intermediate",
            language="Python",
            learning_style="Conceptual",
            icon="dp",
        ),
        PatternExampleResponse(
            id="binary-search",
            title="Binary Search",
            pattern="Binary Search",
            level="Beginner",
            language="Java",
            learning_style="Hands-on",
            icon="search",
        ),
        PatternExampleResponse(
            id="graphs",
            title="Graphs (BFS/DFS)",
            pattern="Graphs",
            level="Intermediate",
            language="C++",
            learning_style="Visual",
            icon="graph",
        ),
        PatternExampleResponse(
            id="monotonic-stack",
            title="Monotonic Stack",
            pattern="Monotonic Stack",
            level="Advanced",
            language="Python",
            learning_style="Visual",
            icon="stack",
        ),
        PatternExampleResponse(
            id="trie",
            title="Trie",
            pattern="Trie",
            level="Intermediate",
            language="JavaScript",
            learning_style="Hands-on",
            icon="tree",
        ),
    ]


__all__ = ["list_examples"]
