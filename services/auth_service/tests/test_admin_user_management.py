"""Admin user management service unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.enums import Role
from app.services.admin_user_management_service import AdminUserManagementService
from shared.exceptions.base import BusinessException


def test_block_user_sets_blocked_flags() -> None:
    user_id = uuid4()
    actor_id = uuid4()
    user = MagicMock()
    user.id = user_id
    user.is_blocked = False
    user.role = Role.USER

    updated = MagicMock()
    updated.id = user_id
    updated.first_name = "A"
    updated.last_name = "B"
    updated.email = "u@example.com"
    updated.role = Role.USER
    updated.is_verified = True
    updated.is_active = True
    updated.is_blocked = True
    updated.disabled_at = None
    updated.blocked_at = MagicMock()
    updated.blocked_reason = "abuse"
    updated.email_verified_at = None
    updated.created_at = MagicMock()
    updated.updated_at = MagicMock()

    users = MagicMock()
    users.get_user_by_id.return_value = user
    users.update_user.return_value = updated
    refresh = MagicMock()
    service = AdminUserManagementService(
        db=MagicMock(),
        user_repository=users,
        refresh_token_repository=refresh,
    )
    result = service.block_user(user_id, actor_id=actor_id, reason="abuse")
    assert result.user.is_blocked is True
    refresh.revoke_all_tokens.assert_called_once_with(user_id)


def test_cannot_block_admin() -> None:
    user = MagicMock()
    user.id = uuid4()
    user.is_blocked = False
    user.role = Role.ADMIN
    users = MagicMock()
    users.get_user_by_id.return_value = user
    service = AdminUserManagementService(
        db=MagicMock(),
        user_repository=users,
        refresh_token_repository=MagicMock(),
    )
    with pytest.raises(BusinessException):
        service.block_user(user.id, actor_id=uuid4(), reason="nope")
