"""Analytics aggregation — thin orchestrator over Usage Service (no SQL)."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.clients.auth_client import AuthServiceClient
from app.clients.usage_client import UsageServiceClient
from app.clients.user_client import UserServiceClient
from app.schemas.admin import (
    AnalyticsDashboardResponse,
    AnalyticsResponse,
    ChartsResponse,
    CostAnalyticsResponse,
    FeatureAnalyticsResponse,
    ModelAnalyticsListResponse,
    ModelAnalyticsResponse,
    ProviderAnalyticsResponse,
    TokenAnalyticsResponse,
    UsageAnalyticsResponse,
    UserUsageDetailAdminResponse,
    UserUsageTableItem,
    UserUsageTableResponse,
)
from app.services.user_management_service import _parse_dt, _to_user_item


class AnalyticsService:
    def __init__(
        self,
        *,
        usage_client: UsageServiceClient,
        auth_client: AuthServiceClient | None = None,
        user_client: UserServiceClient | None = None,
        ai_client: Any | None = None,
    ) -> None:
        self._usage = usage_client
        self._auth = auth_client
        self._user = user_client
        self._ai = ai_client

    # ---- legacy (kept for backward compatibility) -------------------------

    async def get_ai_analytics(self) -> AnalyticsResponse:
        if self._ai is None:
            return AnalyticsResponse()
        data = await self._ai.analytics()
        return AnalyticsResponse(**data)

    async def get_usage_analytics(self) -> UsageAnalyticsResponse:
        usage = await self._usage.analytics()
        models = await self._usage.analytics_models()
        providers = await self._usage.analytics_providers()
        model_items = list(models.get("items", []))
        provider_items = list(providers.get("items", []))
        estimated_cost = sum(float(item.get("estimated_cost", 0)) for item in model_items)
        return UsageAnalyticsResponse(
            total_requests=int(usage.get("total_requests", 0)),
            daily_requests=int(usage.get("daily_requests", 0)),
            monthly_requests=int(usage.get("monthly_requests", 0)),
            token_usage=int(usage.get("token_usage", 0)),
            top_features=list(usage.get("top_features", [])),
            provider_usage=provider_items,
            model_usage=model_items,
            estimated_cost=estimated_cost,
        )

    async def get_model_analytics(self) -> ModelAnalyticsResponse:
        models = await self._usage.analytics_models()
        providers = await self._usage.analytics_providers()
        return ModelAnalyticsResponse(
            provider_usage=list(providers.get("items", [])),
            model_usage=list(models.get("items", [])),
        )

    # ---- /admin/analytics/* -----------------------------------------------

    async def get_dashboard(self) -> AnalyticsDashboardResponse:
        data = await self._usage.analytics_dashboard()
        return AnalyticsDashboardResponse(**data)

    async def get_tokens(self) -> TokenAnalyticsResponse:
        return TokenAnalyticsResponse(**(await self._usage.analytics_tokens()))

    async def get_models(self) -> ModelAnalyticsListResponse:
        return ModelAnalyticsListResponse(**(await self._usage.analytics_models()))

    async def get_providers(self) -> ProviderAnalyticsResponse:
        return ProviderAnalyticsResponse(**(await self._usage.analytics_providers()))

    async def get_features(self) -> FeatureAnalyticsResponse:
        return FeatureAnalyticsResponse(**(await self._usage.analytics_features()))

    async def get_charts(self) -> ChartsResponse:
        return ChartsResponse(**(await self._usage.analytics_charts()))

    async def get_costs(self) -> CostAnalyticsResponse:
        return CostAnalyticsResponse(**(await self._usage.analytics_costs()))

    async def get_users_table(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "total_tokens",
        order: str = "desc",
        search: str | None = None,
        role: str | None = None,
        current_status: str | None = None,
    ) -> UserUsageTableResponse:
        filtered_ids: list[UUID] | None = None
        identity_by_id: dict[str, dict[str, Any]] = {}
        profile_by_id: dict[str, dict[str, Any]] = {}

        if self._auth is not None and (
            search or role or current_status is not None
        ):
            params: dict[str, Any] = {
                "page": 1,
                "page_size": 100,
                "role": role,
            }
            if search:
                if "@" in search:
                    params["email"] = search
                else:
                    params["name"] = search
            auth_data = await self._auth.list_users(params=params)
            items_raw = list(auth_data.get("items", []))
            filtered_ids = [UUID(str(u["id"])) for u in items_raw]
            for u in items_raw:
                identity_by_id[str(u["id"])] = u

        usage_data = await self._usage.analytics_users(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            user_ids=filtered_ids,
        )
        usage_items = list(usage_data.get("items", []))
        missing_ids = [
            UUID(str(item["user_id"]))
            for item in usage_items
            if str(item["user_id"]) not in identity_by_id
        ]
        if self._auth is not None and missing_ids:
            for uid in missing_ids:
                try:
                    identity_by_id[str(uid)] = await self._auth.get_user(uid)
                except Exception:
                    continue

        if self._user is not None and usage_items:
            all_ids = [UUID(str(item["user_id"])) for item in usage_items]
            batch = await self._user.batch_profiles(all_ids)
            for p in batch.get("items", []):
                profile_by_id[str(p["user_id"])] = p

        rows: list[UserUsageTableItem] = []
        for item in usage_items:
            uid = str(item["user_id"])
            identity = identity_by_id.get(uid, {})
            profile = profile_by_id.get(uid, {})
            first = identity.get("first_name") or ""
            last = identity.get("last_name") or ""
            status = profile.get("current_status")
            if current_status and status != current_status:
                continue
            rows.append(
                UserUsageTableItem(
                    user_id=UUID(uid),
                    user_name=f"{first} {last}".strip() or (identity.get("email") or ""),
                    email=identity.get("email") or "",
                    role=str(identity.get("role") or "USER"),
                    current_status=status,
                    total_requests=int(item.get("total_requests", 0)),
                    prompt_tokens=int(item.get("prompt_tokens", 0)),
                    completion_tokens=int(item.get("completion_tokens", 0)),
                    total_tokens=int(item.get("total_tokens", 0)),
                    estimated_cost=float(item.get("estimated_cost", 0)),
                    average_tokens_per_request=float(
                        item.get("average_tokens_per_request", 0)
                    ),
                    last_active=_parse_dt(item.get("last_active")),
                    current_plan=None,
                    most_used_feature=item.get("most_used_feature"),
                    most_used_model=item.get("most_used_model"),
                )
            )

        return UserUsageTableResponse(
            items=rows,
            total=int(usage_data.get("total", len(rows))),
            page=int(usage_data.get("page", page)),
            page_size=int(usage_data.get("page_size", page_size)),
        )

    async def get_user_detail(self, user_id: UUID) -> UserUsageDetailAdminResponse:
        usage_task = self._usage.analytics_user_detail(user_id)
        auth_task = self._auth.get_user(user_id) if self._auth else None
        profile_task = (
            self._user.get_profile_detail(user_id) if self._user else None
        )

        coros: list[Any] = [usage_task]
        if auth_task is not None:
            coros.append(auth_task)
        if profile_task is not None:
            coros.append(profile_task)
        results = await asyncio.gather(*coros, return_exceptions=True)

        usage = results[0] if not isinstance(results[0], BaseException) else {}
        idx = 1
        identity: dict[str, Any] | None = None
        profile_detail: dict[str, Any] | None = None
        if auth_task is not None:
            identity = (
                results[idx]
                if not isinstance(results[idx], BaseException)
                else None
            )
            idx += 1
        if profile_task is not None:
            profile_detail = (
                results[idx]
                if not isinstance(results[idx], BaseException)
                else None
            )

        profile = None
        if isinstance(profile_detail, dict):
            profile = profile_detail.get("profile")
            if not isinstance(profile, dict):
                profile = None

        user_item = None
        if isinstance(identity, dict):
            user_item = _to_user_item(identity, profile)
            # Attach usage totals onto the user card
            user_item.total_requests = int(usage.get("total_requests", 0))
            user_item.prompt_tokens = int(usage.get("prompt_tokens", 0))
            user_item.completion_tokens = int(usage.get("completion_tokens", 0))
            user_item.total_tokens = int(usage.get("total_tokens", 0))
            user_item.estimated_cost = float(usage.get("estimated_cost", 0))
            user_item.last_ai_activity = _parse_dt(usage.get("last_activity"))

        return UserUsageDetailAdminResponse(
            profile=profile,
            user=user_item,
            total_requests=int(usage.get("total_requests", 0)),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            estimated_cost=float(usage.get("estimated_cost", 0)),
            feature_breakdown=list(usage.get("feature_breakdown", [])),
            model_usage=list(usage.get("model_usage", [])),
            provider_usage=list(usage.get("provider_usage", [])),
            session_history=list(usage.get("session_history", [])),
            recent_conversations=list(usage.get("recent_conversations", [])),
            average_execution_time_ms=float(
                usage.get("average_execution_time_ms", 0)
            ),
            last_activity=_parse_dt(usage.get("last_activity")),
        )

    async def export_payload(self, report: str) -> dict[str, Any]:
        return await self._usage.analytics_export(report)
