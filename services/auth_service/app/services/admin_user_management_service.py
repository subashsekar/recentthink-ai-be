"""Admin user-management use cases owned by Auth Service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models.enums import Role
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_users import (
    AdminDashboardIdentityStats,
    AdminMutationResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserIdsResponse,
)
from sqlalchemy.orm import Session

from shared.exceptions.base import BusinessException
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


class AdminUserManagementService:
    """Identity mutations and reads for the Admin Service (via internal HTTP)."""

    def __init__(
        self,
        *,
        db: Session,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._db = db
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository

    def get_dashboard_stats(self) -> AdminDashboardIdentityStats:
        today_start = datetime.now(tz=UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        counts = self._users.dashboard_counts(today_start=today_start)
        return AdminDashboardIdentityStats(**counts)

    def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        email: str | None = None,
        role: Role | None = None,
        is_verified: bool | None = None,
        is_blocked: bool | None = None,
        is_active: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> AdminUserListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        users, total = self._users.list_users(
            skip=skip,
            limit=page_size,
            name=name,
            email=email,
            role=role,
            is_verified=is_verified,
            is_blocked=is_blocked,
            is_active=is_active,
            created_from=created_from,
            created_to=created_to,
            sort=sort,
            order=order,
        )
        return AdminUserListResponse(
            items=[AdminUserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_user(self, user_id: UUID) -> AdminUserResponse:
        user = self._require_user(user_id)
        return AdminUserResponse.model_validate(user)

    def list_user_ids(self) -> AdminUserIdsResponse:
        return AdminUserIdsResponse(user_ids=self._users.list_all_user_ids())

    def block_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> AdminMutationResponse:
        user = self._require_user(user_id)
        self._reject_admin_target(user)
        if user.is_blocked:
            raise BusinessException("User is already blocked.")

        updated = self._apply_update(
            user_id,
            is_blocked=True,
            blocked_at=datetime.now(tz=UTC),
            blocked_reason=reason,
        )
        self._refresh_tokens.revoke_all_tokens(user_id)
        log_security_event(
            "admin_blocked_user",
            admin_id=str(actor_id),
            target_user_id=str(user_id),
            reason=reason or "",
        )
        return AdminMutationResponse(
            message="User blocked successfully.",
            user=AdminUserResponse.model_validate(updated),
        )

    def unblock_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> AdminMutationResponse:
        user = self._require_user(user_id)
        if not user.is_blocked:
            raise BusinessException("User is not blocked.")

        updated = self._apply_update(
            user_id,
            is_blocked=False,
            blocked_at=None,
            blocked_reason=None,
        )
        log_security_event(
            "admin_unblocked_user",
            admin_id=str(actor_id),
            target_user_id=str(user_id),
            reason=reason or "",
        )
        return AdminMutationResponse(
            message="User unblocked successfully.",
            user=AdminUserResponse.model_validate(updated),
        )

    def deactivate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> AdminMutationResponse:
        user = self._require_user(user_id)
        self._reject_admin_target(user)
        if not user.is_active:
            raise BusinessException("User is already deactivated.")

        updated = self._apply_update(
            user_id,
            is_active=False,
            disabled_at=datetime.now(tz=UTC),
        )
        self._refresh_tokens.revoke_all_tokens(user_id)
        log_security_event(
            "admin_deactivated_user",
            admin_id=str(actor_id),
            target_user_id=str(user_id),
            reason=reason or "",
        )
        return AdminMutationResponse(
            message="User deactivated successfully.",
            user=AdminUserResponse.model_validate(updated),
        )

    def activate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> AdminMutationResponse:
        user = self._require_user(user_id)
        if user.is_active:
            raise BusinessException("User is already active.")

        updated = self._apply_update(
            user_id,
            is_active=True,
            disabled_at=None,
        )
        log_security_event(
            "admin_activated_user",
            admin_id=str(actor_id),
            target_user_id=str(user_id),
            reason=reason or "",
        )
        return AdminMutationResponse(
            message="User activated successfully.",
            user=AdminUserResponse.model_validate(updated),
        )

    def delete_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> None:
        user = self._require_user(user_id)
        self._reject_admin_target(user)
        try:
            self._refresh_tokens.revoke_all_tokens(user_id, commit=False)
            self._users.delete_user(user_id)
        except Exception:
            self._db.rollback()
            raise
        log_security_event(
            "admin_deleted_user",
            admin_id=str(actor_id),
            target_user_id=str(user_id),
            reason=reason or "",
        )
        logger.info("Admin deleted user_id=%s actor_id=%s", user_id, actor_id)

    def _apply_update(self, user_id: UUID, **fields: object) -> User:
        try:
            return self._users.update_user(user_id, commit=True, **fields)
        except Exception:
            self._db.rollback()
            raise

    def _require_user(self, user_id: UUID) -> User:
        user = self._users.get_user_by_id(user_id)
        if user is None:
            raise RecordNotFoundError(f"User with id '{user_id}' not found.")
        return user

    @staticmethod
    def _reject_admin_target(user: User) -> None:
        if user.role in {Role.ADMIN, Role.SUPER_ADMIN}:
            raise BusinessException(
                "Cannot perform this action on an administrator account.",
            )
