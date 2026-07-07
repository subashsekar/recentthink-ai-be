"""Memory engine and pruner unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.agents.shared.memory.engine import MemoryEngine
from app.agents.shared.memory.pruner import ContextPruner


def test_pruner_limits_recent_messages() -> None:
    pruner = ContextPruner(max_recent_messages=3)
    messages = [{"role": "user", "content": str(i)} for i in range(10)]
    pruned = pruner.prune_recent_messages(messages)
    assert len(pruned) == 3
    assert pruned[0]["content"] == "7"


def test_pruner_truncates_summary() -> None:
    pruner = ContextPruner(max_summary_chars=20)
    result = pruner.prune_summary("a" * 50)
    assert result is not None
    assert len(result) <= 20


def test_memory_engine_load_returns_layers() -> None:
    repo = MagicMock()
    record = MagicMock()
    record.context = {"planner_output": {"feature": "leetcode"}}
    record.summary = "Session summary"
    record.history_summary = None
    record.recent_messages = [{"role": "user", "content": "hi"}]
    record.previous_responses = ["response"]
    record.follow_up_questions = ["What next?"]
    record.memory_version = 1
    repo.get_by_session_id.return_value = record

    engine = MemoryEngine(repo)
    loaded = engine.load(uuid4())
    assert loaded is not None
    assert loaded["summary"] == "Session summary"
    assert loaded["recent_messages"]
    assert loaded["long_term"] == ["response"]


def test_memory_engine_append_exchange() -> None:
    repo = MagicMock()
    repo.get_by_session_id.return_value = None
    engine = MemoryEngine(repo)
    session_id = uuid4()
    user_id = uuid4()
    engine.append_exchange(
        session_id=session_id,
        user_id=user_id,
        user_message="Explain again",
        assistant_response="Sure, let me rephrase.",
        context={"feature": "leetcode"},
    )
    repo.upsert_memory.assert_called_once()


def test_should_summarize_when_many_messages() -> None:
    pruner = ContextPruner(max_recent_messages=5)
    assert pruner.should_summarize(message_count=10, recent_messages=[{}] * 6)
