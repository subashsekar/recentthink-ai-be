"""Profile completion calculation (computed, no persistence)."""

from __future__ import annotations

from collections.abc import Callable

from app.models.profile import UserProfile
from app.schemas.profile import ProfileCompletionResponse

_REQUIRED_FIELDS: tuple[str, ...] = (
    "username",
    "first_name",
    "last_name",
    "bio",
    "current_status",
    "primary_skill",
    "profile_picture_url",
)

_OptionalCheck = tuple[str, Callable[[UserProfile], bool]]

_OPTIONAL_CHECKS: tuple[_OptionalCheck, ...] = (
    ("mobile_number", lambda profile: _is_filled(profile.mobile_number)),
    (
        "college_or_company",
        lambda profile: _is_filled(profile.college) or _is_filled(profile.company),
    ),
    ("github_username", lambda profile: _is_filled(profile.github_username)),
    (
        "linkedin_or_portfolio",
        lambda profile: _is_filled(profile.linkedin_url) or _is_filled(profile.portfolio_url),
    ),
    (
        "leetcode_or_hackerrank",
        lambda profile: _is_filled(profile.leetcode_username)
        or _is_filled(profile.hackerrank_username),
    ),
)


def _is_filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def compute_profile_completion(profile: UserProfile) -> ProfileCompletionResponse:
    """Return completion percent and field breakdown for ``profile``."""
    completed: list[str] = []
    missing: list[str] = []

    for field in _REQUIRED_FIELDS:
        if _is_filled(getattr(profile, field)):
            completed.append(field)
        else:
            missing.append(field)

    for name, check in _OPTIONAL_CHECKS:
        if check(profile):
            completed.append(name)
        else:
            missing.append(name)

    total_tracked = len(_REQUIRED_FIELDS) + len(_OPTIONAL_CHECKS)
    percent = round(len(completed) / total_tracked * 100) if total_tracked else 0
    percent = min(100, max(0, percent))
    is_complete = all(field in completed for field in _REQUIRED_FIELDS)

    return ProfileCompletionResponse(
        percent=percent,
        completed_fields=completed,
        missing_fields=missing,
        is_complete=is_complete,
    )
