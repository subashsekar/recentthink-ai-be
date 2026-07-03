"""Unit tests for shared password policy validation."""

from __future__ import annotations

import pytest

from app.schemas.password_policy import validate_password_strength


def test_validate_password_strength_accepts_strong_password() -> None:
    assert validate_password_strength("SecurePass1!") == "SecurePass1!"


@pytest.mark.parametrize(
    "password",
    [
        "short1!",
        "nouppercase1!",
        "NOLOWERCASE1!",
        "NoDigits!!",
        "NoSpecial1",
    ],
)
def test_validate_password_strength_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_validate_password_strength_rejects_too_long_password() -> None:
    with pytest.raises(ValueError, match="at most"):
        validate_password_strength("Aa1!" + "x" * 125)
