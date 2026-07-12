"""LeetCode problem fetcher unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.agents.leetcode.problem_fetcher import LeetCodeProblemFetcher


@pytest.mark.asyncio
async def test_fetch_by_slug_returns_manual_error_when_content_empty() -> None:
    """Premium/locked problems may return metadata but no statement body."""
    fetcher = LeetCodeProblemFetcher()
    payload = {
        "data": {
            "question": {
                "questionId": "123",
                "title": "Premium Problem",
                "titleSlug": "premium-problem",
                "difficulty": "Medium",
                "content": "",
                "exampleTestcases": "",
                "topicTags": [{"name": "Array", "slug": "array"}],
            },
        },
    }
    mock_response = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("POST", "https://leetcode.com/graphql"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await fetcher.fetch_by_slug("premium-problem")

    assert not result.success
    assert result.problem is None
    assert result.error
    assert "paste" in result.error.lower()


@pytest.mark.asyncio
async def test_fetch_by_slug_succeeds_with_realistic_content() -> None:
    fetcher = LeetCodeProblemFetcher()
    html = (
        "<p>Given an array of integers <code>nums</code> and an integer "
        "<code>target</code>, return indices of the two numbers such that "
        "they add up to <code>target</code>.</p>"
    )
    payload = {
        "data": {
            "question": {
                "questionId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
                "content": html,
                "exampleTestcases": "1\n2",
                "topicTags": [{"name": "Array", "slug": "array"}],
            },
        },
    }
    mock_response = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("POST", "https://leetcode.com/graphql"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await fetcher.fetch_by_slug("two-sum")

    assert result.success
    assert result.problem is not None
    assert result.problem.title == "Two Sum"
    assert "array of integers" in result.problem.description.lower()
