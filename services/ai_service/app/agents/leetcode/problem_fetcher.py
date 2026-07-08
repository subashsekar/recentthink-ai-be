"""LeetCode problem retrieval via the public GraphQL API."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.agents.leetcode.schemas import ProblemData, ProblemExample
from app.utils.html_text import html_to_text
from app.utils.leetcode_markdown import parse_leetcode_html, plain_text_to_markdown
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

        raw_html = question.get("content") or ""
        markdown, parsed_examples, constraints = parse_leetcode_html(raw_html)
        examples = [
            ProblemExample(
                input=item.input,
                output=item.output,
                explanation=item.explanation,
            )
            for item in parsed_examples
        ]
        description = html_to_text(raw_html)
        topics = [tag["name"] for tag in question.get("topicTags") or [] if tag.get("name")]

        problem = ProblemData(
            title=question.get("title") or slug,
            slug=question.get("titleSlug") or slug,
            url=canonical_url or normalize_leetcode_url(slug),
            description=description,
            difficulty=question.get("difficulty"),
            examples=examples,
            constraints=constraints,
            topics=topics,
            problem_statement_markdown=markdown or plain_text_to_markdown(description),
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
        stripped = statement.strip()
        markdown = plain_text_to_markdown(stripped)
        return ProblemData(
            title=title,
            slug=safe_slug,
            url=normalize_leetcode_url(safe_slug),
            description=stripped,
            difficulty=None,
            examples=[],
            constraints=self._extract_constraints_from_text(stripped),
            topics=[],
            problem_statement_markdown=markdown,
        )

    @staticmethod
    def _extract_constraints_from_text(text: str) -> list[str]:
        constraints: list[str] = []
        capture = False
        stop_prefixes = ("follow-up", "follow up", "example", "note:")
        for line in text.splitlines():
            lower = line.lower().strip()
            if "constraint" in lower:
                capture = True
                continue
            if capture:
                if not line.strip():
                    break
                if any(lower.startswith(prefix) for prefix in stop_prefixes):
                    break
                constraints.append(line.strip())
        return constraints
