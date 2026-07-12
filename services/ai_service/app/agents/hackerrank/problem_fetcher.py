"""HackerRank problem retrieval via embedded page JSON and HTML metadata (best-effort)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.agents.hackerrank.schemas import ProblemData, ProblemExample
from app.utils.hackerrank_url import extract_hackerrank_slug, normalize_hackerrank_url
from app.utils.html_text import html_to_text
from shared.logging import get_logger

logger = get_logger(__name__)

_MIN_DESCRIPTION_LEN = 40
_MIN_REGEX_DESCRIPTION_LEN = 80

_DESCRIPTION_KEYS = frozenset(
    {
        "problem_description",
        "problem_statement",
        "challenge_body",
        "problem_body",
        "body",
        "description",
        "statement",
        "html_body",
        "content",
    },
)
_TITLE_KEYS = frozenset({"name", "title", "challenge_name", "challenge_title"})
_DIFFICULTY_KEYS = frozenset({"difficulty_name", "difficulty", "level"})


@dataclass(frozen=True)
class ProblemFetchResult:
    """Outcome of a problem fetch attempt."""

    success: bool
    problem: ProblemData | None = None
    error: str | None = None


@dataclass(frozen=True)
class _EmbeddedChallengeMeta:
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None


class HackerrankProblemFetcher:
    """Fetches and normalizes HackerRank challenge data from a URL or slug.

    Fetch strategy (Step A first):
    1. Parse embedded JSON (__NEXT_DATA__, Apollo state, application/json scripts)
    2. Fall back to og:description meta tags
    3. Fall back to regex on inline JSON strings in HTML

    If all strategies fail, the service returns MANUAL_REQUIRED for user paste.
    """

    async def fetch_from_url(self, url: str) -> ProblemFetchResult:
        try:
            slug = extract_hackerrank_slug(str(url))
        except ValueError as exc:
            return ProblemFetchResult(success=False, error=str(exc))
        return await self.fetch_by_slug(slug, canonical_url=str(url))

    async def fetch_by_slug(
        self,
        slug: str,
        *,
        canonical_url: str | None = None,
    ) -> ProblemFetchResult:
        url = canonical_url or normalize_hackerrank_url(slug)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RecentThink/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as exc:
            logger.warning("HackerRank fetch HTTP error slug=%s: %s", slug, exc)
            return ProblemFetchResult(
                success=False,
                error="Unable to retrieve the challenge from HackerRank. Please paste the problem statement manually.",
            )

        embedded = _extract_embedded_meta(html)
        title = embedded.title or self._extract_title(html) or slug.replace("-", " ").title()
        description = embedded.description or self._extract_description_fallback(html)
        if not description:
            logger.info("HackerRank description extraction failed slug=%s", slug)
            return ProblemFetchResult(
                success=False,
                error="Could not extract the problem statement from HackerRank. Please paste it manually.",
            )

        problem = ProblemData(
            title=title,
            slug=slug,
            url=normalize_hackerrank_url(slug),
            description=description,
            difficulty=embedded.difficulty or self._extract_difficulty(html),
            examples=self._extract_examples(description),
            constraints=self._extract_constraints(description),
            topics=self._extract_topics(html),
            tags=self._extract_tags(html),
            domain=self._extract_domain(html),
            problem_statement_markdown=description.strip(),
        )
        return ProblemFetchResult(success=True, problem=problem)

    def build_from_manual_input(
        self,
        *,
        title: str,
        statement: str,
        slug: str | None = None,
        url: str | None = None,
    ) -> ProblemData:
        safe_slug = slug or title.lower().replace(" ", "-")
        return ProblemData(
            title=title,
            slug=safe_slug,
            url=url or normalize_hackerrank_url(safe_slug),
            description=statement.strip(),
            difficulty=None,
            examples=self._extract_examples(statement),
            constraints=self._extract_constraints(statement),
            topics=[],
            tags=[],
            domain=None,
            problem_statement_markdown=statement.strip(),
        )

    @staticmethod
    def _extract_title(html: str) -> str | None:
        og = _meta_content(html, r'property=["\']og:title["\']')
        if og:
            return og.strip()
        match = _re_search(html, r"<title>(.*?)</title>")
        if match:
            return _strip_tags(match).strip()
        return None

    @staticmethod
    def _extract_description_fallback(html: str) -> str:
        """Step B/C fallbacks when embedded JSON did not yield a description."""
        og_desc = _meta_content(html, r'property=["\']og:description["\']')
        if og_desc and len(og_desc.strip()) >= _MIN_DESCRIPTION_LEN:
            return og_desc.strip()

        candidates: list[str] = []
        for pattern in (
            r'"problem_description"\s*:\s*"([^"]{%d,})"' % _MIN_REGEX_DESCRIPTION_LEN,
            r'"problem_statement"\s*:\s*"([^"]{%d,})"' % _MIN_REGEX_DESCRIPTION_LEN,
            r'"body"\s*:\s*"([^"]{%d,})"' % _MIN_REGEX_DESCRIPTION_LEN,
            r'"description"\s*:\s*"([^"]{%d,})"' % _MIN_REGEX_DESCRIPTION_LEN,
        ):
            raw = _re_search(html, pattern)
            if raw:
                candidates.append(_normalize_text(_unescape_json_string(raw)))
        return max(candidates, key=len, default="").strip()

    @staticmethod
    def _extract_difficulty(html: str) -> str | None:
        for pattern in (
            r'"difficulty_name"\s*:\s*"([^"]+)"',
            r'"difficulty"\s*:\s*"([^"]+)"',
        ):
            raw = _re_search(html, pattern)
            if raw:
                return raw.strip()
        return None

    @staticmethod
    def _extract_domain(html: str) -> str | None:
        for key in ("Algorithms", "Data Structures", "SQL", "Regex", "Linux", "Java", "Python"):
            if key.lower() in html.lower():
                return key
        return None

    @staticmethod
    def _extract_topics(_html: str) -> list[str]:
        return []

    @staticmethod
    def _extract_tags(_html: str) -> list[str]:
        return []

    @staticmethod
    def _extract_examples(text: str) -> list[ProblemExample]:
        lower = text.lower()
        if "sample input" not in lower or "sample output" not in lower:
            return []
        input_block = _section_after(text, "sample input")
        output_block = _section_after(text, "sample output")
        if not input_block or not output_block:
            return []
        return [ProblemExample(input=input_block.strip(), output=output_block.strip(), explanation=None)]

    @staticmethod
    def _extract_constraints(text: str) -> list[str]:
        lower = text.lower()
        if "constraints" not in lower:
            return []
        block = _section_after(text, "constraints")
        if not block:
            return []
        items = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                break
            if stripped.lower().startswith(("sample", "input", "output", "explanation", "note")):
                break
            items.append(stripped.lstrip("-").strip())
        return [item for item in items if item]


def _extract_embedded_meta(html: str) -> _EmbeddedChallengeMeta:
    """Step A: walk embedded JSON blobs for challenge metadata."""
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None

    for payload in _iter_embedded_json_payloads(html):
        if not description:
            description = _walk_for_longest_string(payload, keys=_DESCRIPTION_KEYS, min_len=_MIN_DESCRIPTION_LEN)
        if not title:
            title = _walk_for_first_string(payload, keys=_TITLE_KEYS, min_len=2)
        if not difficulty:
            difficulty = _walk_for_first_string(payload, keys=_DIFFICULTY_KEYS, min_len=2)

    return _EmbeddedChallengeMeta(
        title=_normalize_text(title) if title else None,
        description=_normalize_text(description) if description else None,
        difficulty=difficulty.strip() if difficulty else None,
    )


def _iter_embedded_json_payloads(html: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_payload(raw: object) -> None:
        if not isinstance(raw, dict):
            return
        fingerprint = json.dumps(raw, sort_keys=True, default=str)[:500]
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        payloads.append(raw)

    next_data = _extract_next_data(html)
    if next_data is not None:
        add_payload(next_data)

    apollo = _extract_apollo_state(html)
    if apollo is not None:
        add_payload(apollo)

    for script_json in _extract_application_json_scripts(html):
        add_payload(script_json)

    return payloads


def _extract_next_data(html: str) -> dict[str, Any] | None:
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_apollo_state(html: str) -> dict[str, Any] | None:
    marker = "window.__APOLLO_STATE__"
    idx = html.find(marker)
    if idx == -1:
        return None
    brace = html.find("{", idx)
    if brace == -1:
        return None
    try:
        parsed, _ = json.JSONDecoder().raw_decode(html, brace)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_application_json_scripts(html: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            results.append(parsed)
    return results


def _walk_for_longest_string(
    obj: Any,
    *,
    keys: frozenset[str],
    min_len: int,
) -> str:
    best = ""

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if key_lower in keys and isinstance(value, str):
                text = _normalize_text(value)
                if len(text) > len(best):
                    best = text
            nested = _walk_for_longest_string(value, keys=keys, min_len=min_len)
            if len(nested) > len(best):
                best = nested
    elif isinstance(obj, list):
        for item in obj:
            nested = _walk_for_longest_string(item, keys=keys, min_len=min_len)
            if len(nested) > len(best):
                best = nested

    return best if len(best) >= min_len else ""


def _walk_for_first_string(
    obj: Any,
    *,
    keys: frozenset[str],
    min_len: int,
) -> str | None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in keys and isinstance(value, str):
                text = _normalize_text(value)
                if len(text) >= min_len:
                    return text
        for value in obj.values():
            found = _walk_for_first_string(value, keys=keys, min_len=min_len)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _walk_for_first_string(item, keys=keys, min_len=min_len)
            if found:
                return found
    return None


def _normalize_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if "<" in stripped and ">" in stripped:
        return html_to_text(stripped)
    return _unescape_json_string(stripped)


def _re_search(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else None


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _meta_content(html: str, attr_pattern: str) -> str | None:
    pattern = rf"<meta[^>]*{attr_pattern}[^>]*content=['\"]([^'\"]+)['\"][^>]*>"
    return _re_search(html, pattern)


def _unescape_json_string(value: str) -> str:
    return (
        value.replace(r"\n", "\n")
        .replace(r"\t", "\t")
        .replace(r"\/", "/")
        .replace(r"\\", "\\")
        .replace(r"\"", '"')
    )


def _section_after(text: str, header: str) -> str:
    idx = text.lower().find(header.lower())
    if idx == -1:
        return ""
    after = text[idx + len(header) :]
    stop_headers = [
        "sample input",
        "sample output",
        "constraints",
        "explanation",
        "notes",
        "input format",
        "output format",
    ]
    stops = [after.lower().find(h) for h in stop_headers if after.lower().find(h) != -1]
    end = min(stops) if stops else len(after)
    return after[:end].strip(" :\n\r\t")
