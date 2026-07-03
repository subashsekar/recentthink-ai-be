"""Unit tests for PasswordService."""

from __future__ import annotations

from app.services.password_service import PasswordService


def test_hash_produces_verifiable_hash() -> None:
    service = PasswordService()
    hashed = service.hash("SecurePass1")

    assert hashed != "SecurePass1"
    assert service.verify("SecurePass1", hashed)


def test_verify_rejects_wrong_password() -> None:
    service = PasswordService()
    hashed = service.hash("SecurePass1")

    assert not service.verify("WrongPass1", hashed)
