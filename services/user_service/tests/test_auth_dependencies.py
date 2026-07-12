"""JWT dependency unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from shared.exceptions.auth import ForbiddenError, InvalidTokenError
from shared.security.jwt import TokenType


def test_get_current_user_success() -> None:
    from app.dependencies.auth import get_current_user

    user_id = uuid4()
    credentials = MagicMock()
    credentials.credentials = "token"
    with patch(
        "app.dependencies.auth.verify_token",
        return_value={
            "token_type": TokenType.ACCESS.value,
            "user_id": str(user_id),
            "email": "a@b.com",
            "role": "USER",
        },
    ):
        user = get_current_user(credentials)
    assert user.user_id == user_id
    assert user.email == "a@b.com"
    assert not user.is_admin


def test_get_current_user_rejects_bad_type() -> None:
    from app.dependencies.auth import get_current_user

    credentials = MagicMock()
    credentials.credentials = "token"
    with patch(
        "app.dependencies.auth.verify_token",
        return_value={
            "token_type": "refresh",
            "user_id": str(uuid4()),
            "email": "a",
            "role": "USER",
        },
    ):
        with pytest.raises(InvalidTokenError):
            get_current_user(credentials)


def test_require_admin_user() -> None:
    from app.dependencies.auth import AuthenticatedUser, require_admin_user

    admin = AuthenticatedUser(user_id=uuid4(), email="a@b.com", role="ADMIN")
    assert require_admin_user(admin) is admin

    user = AuthenticatedUser(user_id=uuid4(), email="u@b.com", role="USER")
    with pytest.raises(ForbiddenError):
        require_admin_user(user)
