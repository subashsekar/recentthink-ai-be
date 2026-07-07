"""LeetCode problem retrieval via the public GraphQL API."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.agents.leetcode.schemas import ProblemData, ProblemExample
from app.utils.html_text import html_to_text
from app.utils.leetcode_url import extract_leetcode_slug, normalize_leetcode_url
from shared.logging import get_logger

logger = get_logger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

QUESTION_QUERY = """
query questionContent($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    title
    titleSlug
    difficulty
    content
    exampleTestcases
    topicTags {
      name
      slug
    }
  }
}
"""


@dataclass(frozen=True)
class ProblemFetchResult:
    """Outcome of a problem fetch attempt."""

    success: bool
    problem: ProblemData | None = None
    error: str | None = None


class LeetCodeProblemFetcher:
    """Fetches and normalizes LeetCode problem data from a URL or slug."""

    async def fetch_from_url(self, url: str) -> ProblemFetchResult:
        try:
            slug = extract_leetcode_slug(str(url))
        except ValueError as exc:
            return ProblemFetchResult(success=False, error=str(exc))
        return await self.fetch_by_slug(slug, canonical_url=str(url))

    async def fetch_by_slug(
        self,
        slug: str,
        *,
        canonical_url: str | None = None,
    ) -> ProblemFetchResult:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RecentThink/1.0",
            "Referer": "https://leetcode.com",
        }
        payload = {
            "query": QUESTION_QUERY,
            "variables": {"titleSlug": slug},
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(
                    LEETCODE_GRAPHQL_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("LeetCode fetch HTTP error slug=%s: %s", slug, exc)
            return ProblemFetchResult(
                success=False,
                error="Unable to reach LeetCode. Please paste the problem statement manually.",
            )

        question = data.get("data", {}).get("question")
        if not question:
            logger.warning("LeetCode returned no question for slug=%s", slug)
            return ProblemFetchResult(
                success=False,
                error="Problem not found on LeetCode. Check the URL or paste the statement manually.",
            )

        description = html_to_text(question.get("content") or "")
        examples = self._parse_examples(question.get("exampleTestcases"))
        topics = [tag["name"] for tag in question.get("topicTags") or [] if tag.get("name")]

        problem = ProblemData(
            title=question.get("title") or slug,
            slug=question.get("titleSlug") or slug,
            url=canonical_url or normalize_leetcode_url(slug),
            description=description,
            difficulty=question.get("difficulty"),
            examples=examples,
            constraints=self._extract_constraints(description),
            topics=topics,
        )
        return ProblemFetchResult(success=True, problem=problem)

    def build_from_manual_input(
        self,
        *,
        title: str,
        statement: str,
        slug: str | None = None,
    ) -> ProblemData:
        """Construct problem data from user-provided manual input."""
        safe_slug = slug or title.lower().replace(" ", "-")
        return ProblemData(
            title=title,
            slug=safe_slug,
            url=normalize_leetcode_url(safe_slug),
            description=statement.strip(),
            difficulty=None,
            examples=[],
            constraints=self._extract_constraints(statement),
            topics=[],
        )

    @staticmethod
    def _parse_examples(raw: str | None) -> list[ProblemExample]:
        if not raw:
            return []
        blocks = [block.strip() for block in raw.strip().split("\n") if block.strip()]
        examples: list[ProblemExample] = []
        for index, block in enumerate(blocks):
            lines = block.split("\n")
            examples.append(
                ProblemExample(
                    input=lines[0] if lines else block,
                    output=lines[1] if len(lines) > 1 else "",
                    explanation=f"Example {index + 1}",
                ),
            )
        return examples

    @staticmethod
    def _extract_constraints(description: str) -> list[str]:
        constraints: list[str] = []
        capture = False
        for line in description.splitlines():
            lower = line.lower()
            if "constraint" in lower:
                capture = True
                continue
            if capture:
                if not line.strip():
                    break
                constraints.append(line.strip())
        return constraints
