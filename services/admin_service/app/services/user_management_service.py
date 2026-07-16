"""User management orchestration via Auth / User / AI / Usage HTTP APIs."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from app.clients.ai_client import AIServiceClient
from app.clients.auth_client import AuthServiceClient
from app.clients.usage_client import UsageServiceClient
from app.clients.user_client import UserServiceClient
from app.models.enums import AuditAction
from app.schemas.admin import (
    AdminUserItem,
    MutationResponse,
    UserDetailResponse,
    UserListResponse,
)
from app.services.audit_service import AuditService
from shared.logging import get_logger

logger = get_logger(__name__)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_user_item(
    data: dict[str, Any],
    profile: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> AdminUserItem:
    return AdminUserItem(
        id=UUID(str(data["id"])),
        first_name=data.get("first_name") or "",
        last_name=data.get("last_name") or "",
        email=data.get("email") or "",
        role=str(data.get("role") or "USER"),
        is_verified=bool(data.get("is_verified", False)),
        is_active=bool(data.get("is_active", True)),
        is_blocked=bool(data.get("is_blocked", False)),
        disabled_at=_parse_dt(data.get("disabled_at")),
        blocked_at=_parse_dt(data.get("blocked_at")),
        blocked_reason=data.get("blocked_reason"),
        created_at=_parse_dt(data.get("created_at")),
        username=(profile or {}).get("username"),
        current_status=(profile or {}).get("current_status"),
        primary_skill=(profile or {}).get("primary_skill"),
        profile_picture_url=(profile or {}).get("profile_picture_url"),
        total_requests=int((usage or {}).get("total_requests", 0)),
        prompt_tokens=int((usage or {}).get("prompt_tokens", 0)),
        completion_tokens=int((usage or {}).get("completion_tokens", 0)),
        total_tokens=int((usage or {}).get("total_tokens", 0)),
        estimated_cost=float((usage or {}).get("estimated_cost", 0)),
        last_ai_activity=_parse_dt(
            (usage or {}).get("last_active") or (usage or {}).get("last_activity")
        ),
        most_used_feature=(usage or {}).get("most_used_feature"),
        most_used_model=(usage or {}).get("most_used_model"),
        current_plan=(usage or {}).get("current_plan"),
    )


class UserManagementService:
    def __init__(
        self,
        *,
        auth_client: AuthServiceClient,
        user_client: UserServiceClient,
        ai_client: AIServiceClient,
        usage_client: UsageServiceClient,
        audit_service: AuditService,
    ) -> None:
        self._auth = auth_client
        self._user = user_client
        self._ai = ai_client
        self._usage = usage_client
        self._audit = audit_service

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        email: str | None = None,
        role: str | None = None,
        is_verified: bool | None = None,
        is_blocked: bool | None = None,
        is_active: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "created_at",
        order: str = "desc",
        primary_skill: str | None = None,
        current_status: str | None = None,
    ) -> UserListResponse:
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "name": name,
            "email": email,
            "role": role,
            "is_verified": is_verified,
            "is_blocked": is_blocked,
            "is_active": is_active,
            "created_from": created_from.isoformat() if created_from else None,
            "created_to": created_to.isoformat() if created_to else None,
            "sort": sort,
            "order": order,
        }
        data = await self._auth.list_users(params=params)
        items_raw = data.get("items", [])
        user_ids = [UUID(str(u["id"])) for u in items_raw]
        profiles_by_id: dict[str, dict[str, Any]] = {}
        usage_by_id: dict[str, dict[str, Any]] = {}
        if user_ids:
            batch, usage_batch = await asyncio.gather(
                self._user.batch_profiles(user_ids),
                self._usage.batch_user_stats(user_ids),
            )
            for p in batch.get("items", []):
                profiles_by_id[str(p["user_id"])] = p
            for u in usage_batch.get("items", []):
                usage_by_id[str(u["user_id"])] = u

        # Optional profile-side filters after enrichment
        items = [
            _to_user_item(
                u,
                profiles_by_id.get(str(u["id"])),
                usage_by_id.get(str(u["id"])),
            )
            for u in items_raw
        ]
        if primary_skill:
            items = [i for i in items if i.primary_skill == primary_skill]
        if current_status:
            items = [i for i in items if i.current_status == current_status]

        return UserListResponse(
            items=items,
            total=int(data.get("total", len(items))),
            page=int(data.get("page", page)),
            page_size=int(data.get("page_size", page_size)),
        )

    async def get_user(self, user_id: UUID) -> UserDetailResponse:
        user_data, profile_detail, ai_history, usage, usage_analytics = (
            await asyncio.gather(
                self._auth.get_user(user_id),
                self._user.get_profile_detail(user_id),
                self._ai.user_history(user_id),
                self._usage.user_usage(user_id),
                self._usage.analytics_user_detail(user_id),
            )
        )
        profile = profile_detail.get("profile")
        return UserDetailResponse(
            user=_to_user_item(
                user_data,
                profile if isinstance(profile, dict) else None,
                usage_analytics if isinstance(usage_analytics, dict) else None,
            ),
            profile=profile if isinstance(profile, dict) else None,
            statistics=profile_detail.get("statistics"),
            ai_history=ai_history,
            usage=usage,
            usage_analytics=usage_analytics
            if isinstance(usage_analytics, dict)
            else None,
        )

    async def block_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MutationResponse:
        result = await self._auth.block_user(
            user_id, actor_id=actor_id, reason=reason
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.USER_BLOCKED.value,
            target_user_id=user_id,
            reason=reason,
        )
        return MutationResponse(
            message=result.get("message", "User blocked."),
            user=_to_user_item(result["user"]),
        )

    async def unblock_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MutationResponse:
        result = await self._auth.unblock_user(
            user_id, actor_id=actor_id, reason=reason
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.USER_UNBLOCKED.value,
            target_user_id=user_id,
            reason=reason,
        )
        return MutationResponse(
            message=result.get("message", "User unblocked."),
            user=_to_user_item(result["user"]),
        )

    async def activate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MutationResponse:
        result = await self._auth.activate_user(
            user_id, actor_id=actor_id, reason=reason
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.USER_ACTIVATED.value,
            target_user_id=user_id,
            reason=reason,
        )
        return MutationResponse(
            message=result.get("message", "User activated."),
            user=_to_user_item(result["user"]),
        )

    async def deactivate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MutationResponse:
        result = await self._auth.deactivate_user(
            user_id, actor_id=actor_id, reason=reason
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.USER_DEACTIVATED.value,
            target_user_id=user_id,
            reason=reason,
        )
        return MutationResponse(
            message=result.get("message", "User deactivated."),
            user=_to_user_item(result["user"]),
        )

    async def delete_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> None:
        await self._auth.delete_user(user_id, actor_id=actor_id, reason=reason)
        # Belt-and-suspenders: auth already publishes AccountDeleted → purge;
        # re-call in case auth ran before AI/Usage were reachable.
        await self._best_effort_purge(user_id)
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.USER_DELETED.value,
            target_user_id=user_id,
            reason=reason,
        )

    async def _best_effort_purge(self, user_id: UUID) -> None:
        for name, client in (("ai", self._ai), ("usage", self._usage)):
            try:
                await client.purge_user(user_id)
            except Exception as exc:
                logger.warning(
                    "Post-delete purge failed service=%s user_id=%s error=%s",
                    name,
                    user_id,
                    exc,
                )
