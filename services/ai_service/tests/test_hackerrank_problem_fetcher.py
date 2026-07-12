"""Unit tests for HackerRank problem fetcher (Step A embedded JSON + fallbacks)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.agents.hackerrank.problem_fetcher import (
    HackerrankProblemFetcher,
    _extract_embedded_meta,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hackerrank"


@pytest.mark.asyncio
async def test_fetch_from_url_invalid_url_returns_error() -> None:
    fetcher = HackerrankProblemFetcher()
    result = await fetcher.fetch_from_url("https://example.com/not-hackerrank")
    assert not result.success
    assert result.error


def test_build_from_manual_input_normalizes_problem() -> None:
    fetcher = HackerrankProblemFetcher()
    problem = fetcher.build_from_manual_input(
        title="Manual Challenge",
        statement="Sample Input\n1\nSample Output\n2\nConstraints\n1 <= n <= 10",
        slug="manual-challenge",
        url="https://www.hackerrank.com/challenges/manual-challenge/problem",
    )
    assert problem.slug == "manual-challenge"
    assert problem.examples
    assert problem.constraints


def test_extract_embedded_meta_from_next_data_fixture() -> None:
    html = (FIXTURES / "solve_me_first_next_data.html").read_text(encoding="utf-8")
    meta = _extract_embedded_meta(html)
    assert meta.title == "Solve Me First"
    assert meta.difficulty == "Easy"
    assert meta.description is not None
    assert "solveMeFirst" in meta.description
    assert "a + b" in meta.description


def test_extract_embedded_meta_from_apollo_state() -> None:
    html = """
    <html><body>
    <script>
    window.__APOLLO_STATE__ = {
      "Challenge:123": {
        "name": "Two Strings",
        "difficulty_name": "Easy",
        "body": "<p>Given two strings, determine whether they share a common substring of length two.</p>"
      }
    };
    </script>
    </body></html>
  """
    meta = _extract_embedded_meta(html)
    assert meta.title == "Two Strings"
    assert meta.difficulty == "Easy"
    assert meta.description is not None
    assert "common substring" in meta.description


def test_extract_description_fallback_uses_og_description() -> None:
    html = """
    <html><head>
    <meta property="og:description" content="This is a sufficiently long HackerRank challenge description for fallback extraction." />
    </head></html>
    """
    text = HackerrankProblemFetcher._extract_description_fallback(html)
    assert "sufficiently long" in text


@pytest.mark.asyncio
async def test_fetch_by_slug_uses_embedded_json_from_fixture() -> None:
    html = (FIXTURES / "solve_me_first_next_data.html").read_text(encoding="utf-8")
    fetcher = HackerrankProblemFetcher()

    mock_response = httpx.Response(
        200,
        text=html,
        request=httpx.Request("GET", "https://www.hackerrank.com/challenges/solve-me-first/problem"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await fetcher.fetch_by_slug("solve-me-first")

    assert result.success
    assert result.problem is not None
    assert result.problem.title == "Solve Me First"
    assert result.problem.difficulty == "Easy"
    assert "solveMeFirst" in result.problem.description


@pytest.mark.asyncio
async def test_fetch_by_slug_returns_manual_error_when_no_description() -> None:
    html = "<html><head><title>Empty</title></head><body></body></html>"
    fetcher = HackerrankProblemFetcher()
    mock_response = httpx.Response(
        200,
        text=html,
        request=httpx.Request("GET", "https://www.hackerrank.com/challenges/empty/problem"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await fetcher.fetch_by_slug("empty")

    assert not result.success
    assert result.error
    assert "paste" in result.error.lower()
