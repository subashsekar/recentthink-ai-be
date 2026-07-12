"""Validation helper tests."""

from __future__ import annotations

import pytest
from shared.exceptions.base import ValidationException


def test_normalize_username_trims_and_lowercases() -> None:
    from app.utils.validators import normalize_username

    assert normalize_username("  Alice_Dev  ") == "alice_dev"


def test_normalize_username_rejects_invalid() -> None:
    from app.utils.validators import normalize_username

    with pytest.raises(ValidationException):
        normalize_username("ab")
    with pytest.raises(ValidationException):
        normalize_username("bad-name!")


def test_platform_username_strips_at() -> None:
    from app.utils.validators import normalize_platform_username

    assert normalize_platform_username("@Octocat", field="github_username") == "octocat"


def test_mobile_number_accepts_e164() -> None:
    from app.utils.validators import validate_mobile_number

    assert validate_mobile_number("+1 (555) 123-4567") == "+15551234567"


def test_mobile_number_rejects_invalid() -> None:
    from app.utils.validators import validate_mobile_number

    with pytest.raises(ValidationException):
        validate_mobile_number("123")


def test_linkedin_and_portfolio_urls() -> None:
    from app.utils.validators import validate_http_url, validate_linkedin_url

    assert validate_linkedin_url("https://www.linkedin.com/in/jane") is not None
    assert validate_http_url("https://jane.dev", field="portfolio_url") is not None
    with pytest.raises(ValidationException):
        validate_linkedin_url("https://example.com/in/jane")
    with pytest.raises(ValidationException):
        validate_http_url("ftp://jane.dev", field="portfolio_url")


def test_bio_max_length() -> None:
    from app.utils.validators import validate_bio

    assert validate_bio("  hello  ") == "hello"
    with pytest.raises(ValidationException):
        validate_bio("x" * 501)


def test_blank_optional_becomes_none() -> None:
    from app.utils.validators import normalize_optional_text, normalize_username

    assert normalize_optional_text("   ") is None
    assert normalize_username(None) is None
