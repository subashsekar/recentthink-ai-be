"""Tests for Admin analytics routes and export formatting."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, require_admin_user
from app.dependencies.services import get_analytics_service
from app.main import app
from app.schemas.admin import (
    AnalyticsDashboardResponse,
    ChartsResponse,
    CostAnalyticsResponse,
    FeatureAnalyticsResponse,
    ModelAnalyticsListResponse,
    ProviderAnalyticsResponse,
    TokenAnalyticsResponse,
    UserUsageDetailAdminResponse,
    UserUsageTableResponse,
)
from app.services.report_export import build_export_file


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_client(client: TestClient) -> TestClient:
    admin_id = uuid4()

    def _admin() -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=admin_id,
            email="admin@example.com",
            role="ADMIN",
        )

    class _AnalyticsSvc:
        async def get_dashboard(self) -> AnalyticsDashboardResponse:
            return AnalyticsDashboardResponse(
                total_requests=10,
                total_tokens_used=1000,
                platform_total_requests=10,
                platform_total_tokens=1000,
            )

        async def get_tokens(self) -> TokenAnalyticsResponse:
            return TokenAnalyticsResponse(total_tokens=1000)

        async def get_models(self) -> ModelAnalyticsListResponse:
            return ModelAnalyticsListResponse(
                items=[
                    {
                        "model": "gpt-4o",
                        "provider": "openai",
                        "requests": 5,
                        "total_tokens": 500,
                    }
                ]
            )

        async def get_providers(self) -> ProviderAnalyticsResponse:
            return ProviderAnalyticsResponse(
                items=[{"provider": "openrouter", "requests": 5, "tokens": 500}]
            )

        async def get_features(self) -> FeatureAnalyticsResponse:
            return FeatureAnalyticsResponse(
                items=[{"feature": "leetcode", "requests": 3, "tokens": 300}]
            )

        async def get_charts(self) -> ChartsResponse:
            return ChartsResponse(
                daily_token_usage=[{"label": "2026-07-01", "value": 100}]
            )

        async def get_costs(self) -> CostAnalyticsResponse:
            return CostAnalyticsResponse(total_estimated_cost=1.25)

        async def get_users_table(self, **_kwargs: object) -> UserUsageTableResponse:
            return UserUsageTableResponse(
                items=[
                    {
                        "user_id": uuid4(),
                        "user_name": "Ada Lovelace",
                        "email": "ada@example.com",
                        "total_tokens": 100,
                    }
                ],
                total=1,
                page=1,
                page_size=20,
            )

        async def get_user_detail(self, _user_id: object) -> UserUsageDetailAdminResponse:
            return UserUsageDetailAdminResponse(total_requests=4, total_tokens=200)

        async def export_payload(self, report: str) -> dict:
            return {
                "report": report,
                "columns": ["feature", "requests"],
                "rows": [{"feature": "leetcode", "requests": 3}],
            }

    app.dependency_overrides[require_admin_user] = _admin
    app.dependency_overrides[get_analytics_service] = lambda: _AnalyticsSvc()
    yield client
    app.dependency_overrides.clear()


def test_analytics_dashboard(admin_client: TestClient) -> None:
    response = admin_client.get("/admin/analytics/dashboard")
    assert response.status_code == 200
    assert response.json()["total_requests"] == 10


def test_analytics_nested_routes(admin_client: TestClient) -> None:
    for path in (
        "/admin/analytics/tokens",
        "/admin/analytics/models",
        "/admin/analytics/providers",
        "/admin/analytics/features",
        "/admin/analytics/charts",
        "/admin/analytics/costs",
        "/admin/analytics/users",
    ):
        response = admin_client.get(path)
        assert response.status_code == 200, path


def test_analytics_user_detail(admin_client: TestClient) -> None:
    response = admin_client.get(f"/admin/analytics/users/{uuid4()}")
    assert response.status_code == 200
    assert response.json()["total_tokens"] == 200


def test_analytics_export_csv(admin_client: TestClient) -> None:
    response = admin_client.get(
        "/admin/analytics/export",
        params={"report": "feature_usage", "format": "csv"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert b"leetcode" in response.content


def test_build_export_excel_and_pdf() -> None:
    columns = ["feature", "requests"]
    rows = [{"feature": "leetcode", "requests": 3}]
    xlsx, media, name = build_export_file(
        report="feature_usage", columns=columns, rows=rows, fmt="excel"
    )
    assert media.startswith("application/vnd.openxmlformats")
    assert name.endswith(".xlsx")
    assert xlsx[:2] == b"PK"

    pdf, pdf_media, pdf_name = build_export_file(
        report="feature_usage", columns=columns, rows=rows, fmt="pdf"
    )
    assert pdf_media == "application/pdf"
    assert pdf_name.endswith(".pdf")
    assert pdf.startswith(b"%PDF")


def test_analytics_requires_auth(client: TestClient) -> None:
    response = client.get("/admin/analytics/dashboard")
    assert response.status_code in {401, 403}
