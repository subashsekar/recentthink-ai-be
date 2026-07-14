"""Cache key builder tests."""

from __future__ import annotations

from app.cache.cache_keys import (
    build_course_key,
    build_dsa_key,
    build_feature_key,
    build_hackerrank_key,
    build_leetcode_key,
    is_cacheable_feature,
    normalize_segment,
    sha256_hex,
)


def test_cacheable_features() -> None:
    assert is_cacheable_feature("leetcode")
    assert is_cacheable_feature("hackerrank")
    assert is_cacheable_feature("dsa_pattern")
    assert is_cacheable_feature("course_generator")
    assert not is_cacheable_feature("interview")
    assert not is_cacheable_feature("followup")


def test_keys_are_sha256_digests_not_raw_prompts() -> None:
    prompt = "Explain this secret prompt " * 20
    key = build_leetcode_key(model="m", prompt_version="v1", problem_slug=prompt)
    assert key.startswith("leetcode:")
    assert prompt not in key
    assert sha256_hex(
        f"{normalize_segment('m')}|{normalize_segment('v1')}|{normalize_segment(prompt)}",
    ) in key


def test_feature_key_builders() -> None:
    assert build_hackerrank_key(
        model="m",
        prompt_version="v1",
        challenge_slug="solve-me",
    ).startswith("hackerrank:")
    assert build_dsa_key(pattern="two-pointers", difficulty="medium", model="m").startswith(
        "dsa:",
    )
    assert build_course_key(
        topic="python",
        level="beginner",
        language="en",
        model="m",
    ).startswith("course:")


def test_build_feature_key_routes() -> None:
    assert (
        build_feature_key(
            feature="leetcode",
            model="m",
            prompt_version="v1",
            context={"slug": "two-sum"},
        )
        is not None
    )
    assert (
        build_feature_key(
            feature="hackerrank",
            model="m",
            prompt_version="v1",
            context={"slug": "c1"},
        )
        is not None
    )
    assert (
        build_feature_key(
            feature="dsa_pattern",
            model="m",
            prompt_version="v1",
            context={"pattern": "sliding-window", "difficulty": "easy"},
        )
        is not None
    )
    assert (
        build_feature_key(
            feature="course_generator",
            model="m",
            prompt_version="v1",
            context={"topic": "python", "level": "beginner", "language": "en"},
        )
        is not None
    )
    assert (
        build_feature_key(
            feature="interview",
            model="m",
            prompt_version="v1",
            context={"role": "backend"},
        )
        is None
    )


def test_normalize_empty() -> None:
    assert normalize_segment("   ") == "empty"
