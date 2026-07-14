"""Deterministic SHA-256 cache keys for AI product features.

Never use raw prompts as keys. Long segments are hashed.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Final

_SAFE_SEGMENT: Final[re.Pattern[str]] = re.compile(r"[^a-zA-Z0-9._:-]+")
_MAX_RAW_SEGMENT_LEN: Final[int] = 64

# Features eligible for response caching (user-independent content only).
CACHEABLE_FEATURES: Final[frozenset[str]] = frozenset(
    {
        "leetcode",
        "hackerrank",
        "dsa",
        "dsa_pattern",
        "course_generator",
    },
)


def sha256_hex(value: str) -> str:
    """Return the SHA-256 hex digest of ``value``."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_segment(value: str, *, max_len: int = _MAX_RAW_SEGMENT_LEN) -> str:
    """Sanitize a key segment; hash when longer than ``max_len``."""
    cleaned = _SAFE_SEGMENT.sub("-", value.strip().lower()).strip("-")
    if not cleaned:
        return "empty"
    if len(cleaned) > max_len:
        return sha256_hex(value)
    return cleaned


def is_cacheable_feature(feature: str) -> bool:
    """Return ``True`` when responses for ``feature`` may be cached."""
    return feature.strip().lower() in CACHEABLE_FEATURES


def build_leetcode_key(*, model: str, prompt_version: str, problem_slug: str) -> str:
    digest = sha256_hex(
        f"{normalize_segment(model)}|{normalize_segment(prompt_version)}|"
        f"{normalize_segment(problem_slug)}",
    )
    return f"leetcode:{digest}"


def build_hackerrank_key(
    *,
    model: str,
    prompt_version: str,
    challenge_slug: str,
) -> str:
    digest = sha256_hex(
        f"{normalize_segment(model)}|{normalize_segment(prompt_version)}|"
        f"{normalize_segment(challenge_slug)}",
    )
    return f"hackerrank:{digest}"


def build_dsa_key(*, pattern: str, difficulty: str, model: str) -> str:
    digest = sha256_hex(
        f"{normalize_segment(pattern)}|{normalize_segment(difficulty)}|"
        f"{normalize_segment(model)}",
    )
    return f"dsa:{digest}"


def build_course_key(
    *,
    topic: str,
    level: str,
    language: str,
    model: str,
) -> str:
    digest = sha256_hex(
        f"{normalize_segment(topic)}|{normalize_segment(level)}|"
        f"{normalize_segment(language)}|{normalize_segment(model)}",
    )
    return f"course:{digest}"


def build_feature_key(
    *,
    feature: str,
    model: str,
    prompt_version: str,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    message: str = "",
) -> str | None:
    """Build a deterministic cache key, or ``None`` if the feature is not cacheable."""
    feature_l = feature.strip().lower()
    if not is_cacheable_feature(feature_l):
        return None

    ctx = context or {}
    meta = metadata or {}

    if feature_l == "leetcode":
        slug = str(
            ctx.get("slug")
            or meta.get("problem_slug")
            or ctx.get("title")
            or message
            or "unknown",
        )
        return build_leetcode_key(
            model=model,
            prompt_version=prompt_version,
            problem_slug=slug,
        )
    if feature_l == "hackerrank":
        slug = str(
            ctx.get("slug")
            or meta.get("challenge_slug")
            or ctx.get("title")
            or message
            or "unknown",
        )
        return build_hackerrank_key(
            model=model,
            prompt_version=prompt_version,
            challenge_slug=slug,
        )
    if feature_l in {"dsa_pattern", "dsa"}:
        return build_dsa_key(
            pattern=str(ctx.get("pattern") or meta.get("pattern") or message or "unknown"),
            difficulty=str(ctx.get("difficulty") or meta.get("difficulty") or "any"),
            model=model,
        )
    if feature_l in {"course_generator", "course"}:
        return build_course_key(
            topic=str(ctx.get("topic") or meta.get("topic") or message or "unknown"),
            level=str(ctx.get("level") or meta.get("level") or "any"),
            language=str(ctx.get("language") or meta.get("language") or "en"),
            model=model,
        )
    return None
