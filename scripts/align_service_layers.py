"""Align all microservices with clean-architecture layer responsibilities."""

from __future__ import annotations

from pathlib import Path

SERVICES: list[tuple[str, str]] = [
    ("gateway", "RecentThink API Gateway"),
    ("auth_service", "RecentThink Auth Service"),
    ("user_service", "RecentThink User Service"),
    ("admin_service", "RecentThink Admin Service"),
    ("ai_service", "RecentThink AI Service"),
    ("usage_service", "RecentThink Usage Service"),
]

HEALTH_SCHEMA = '''"""Health check response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health status returned by the service root endpoint."""

    service: str
    status: str
'''

HEALTH_SERVICE = '''"""Health check business logic."""

from __future__ import annotations

from app.core.config import SERVICE_NAME
from app.schemas.health import HealthResponse

HEALTHY_STATUS = "healthy"


def get_health_status() -> HealthResponse:
    """Build the current service health payload."""
    return HealthResponse(service=SERVICE_NAME, status=HEALTHY_STATUS)
'''

HEALTH_API = '''"""Health check HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import get_health_status

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service health status."""
    return get_health_status()
'''

MAIN_TEMPLATE = '''"""{title} ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    # Startup placeholder
    yield
    # Shutdown placeholder


app = FastAPI(
    title="{title}",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(health_router)
'''

root = Path(__file__).resolve().parents[1] / "services"

for service_name, title in SERVICES:
    app_dir = root / service_name / "app"
    (app_dir / "schemas" / "health.py").write_text(HEALTH_SCHEMA, encoding="utf-8")
    (app_dir / "services" / "health_service.py").write_text(HEALTH_SERVICE, encoding="utf-8")
    (app_dir / "api" / "health.py").write_text(HEALTH_API, encoding="utf-8")
    (app_dir / "main.py").write_text(MAIN_TEMPLATE.format(title=title), encoding="utf-8")
    print(f"Aligned layers for {service_name}")
