"""Tests for teacher payload parsing."""

from __future__ import annotations

from app.agents.shared.teacher.parser import parse_teacher_payload


def test_parse_teacher_payload_from_json_object() -> None:
    payload = parse_teacher_payload(
        '{"problem_summary":"Two Sum","explanation":"Use a hash map.","concepts":["Hash Map"]}',
    )
    assert "hash map" in payload["explanation"].lower()
    assert payload["concepts"] == ["Hash Map"]


def test_parse_teacher_payload_from_wrapped_teacher_key() -> None:
    payload = parse_teacher_payload(
        '{"teacher":{"explanation":"Try sorting first.","approach":"Sort and scan"}}',
    )
    assert "sort" in payload["explanation"].lower()
    assert payload["thinking_process"] == "Sort and scan"


def test_parse_teacher_payload_falls_back_for_broken_json() -> None:
    payload = parse_teacher_payload('{"problem_summary": "unfinished')
    assert payload["explanation"]
    assert "unfinished" in payload["explanation"]


def test_parse_teacher_payload_enriches_from_planner_metadata() -> None:
    payload = parse_teacher_payload(
        "{}",
        planner_metadata={
            "patterns": ["Array"],
            "learning_objectives": ["Spot duplicates"],
        },
    )
    assert payload["concepts"] == ["Array"]
    assert payload["learning_objectives"] == ["Spot duplicates"]
