"""Align all microservices with clean-architecture layer responsibilities."""

from __future__ import annotations

from pathlib import Path

SERVICES: list[tuple[str, str, str]] = [
    ("gateway", "RecentThink API Gateway", "/"),
    ("auth_service", "RecentThink Auth Service", "/health"),
    ("user_service", "RecentThink User Service", "/"),
    ("admin_service", "RecentThink Admin Service", "/"),
    ("ai_service", "RecentThink AI Service", "/"),
    ("usage_service", "RecentThink Usage Service", "/"),
]

AUTH_MAIN = '''"""RecentThink Auth Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.database import router as database_router
from app.api.health import router as health_router

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    yield


app = FastAPI(
    title="RecentThink Auth Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(database_router)
app.include_router(health_router)
'''

HEALTH_SERVICE = '''"""Health check business logic."""

from __future__ import annotations

from app.core.config import SERVICE_NAME
from shared.schemas.health import HealthResponse, build_health_response


def get_health_status() -> HealthResponse:
    """Build the current service health payload."""
    return build_health_response(SERVICE_NAME)
'''

HEALTH_API_TEMPLATE = '''"""Health check HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.health_service import get_health_status
from shared.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("{route}", response_model=HealthResponse)
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
    yield


app = FastAPI(
    title="{title}",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(health_router)
'''

root = Path(__file__).resolve().parents[1] / "services"

for service_name, title, health_route in SERVICES:
    app_dir = root / service_name / "app"
    health_schema = app_dir / "schemas" / "health.py"
    if health_schema.exists():
        health_schema.unlink()
    (app_dir / "services" / "health_service.py").write_text(
        HEALTH_SERVICE, encoding="utf-8"
    )
    (app_dir / "api" / "health.py").write_text(
        HEALTH_API_TEMPLATE.format(route=health_route),
        encoding="utf-8",
    )
    if service_name == "auth_service":
        (app_dir / "main.py").write_text(AUTH_MAIN, encoding="utf-8")
    else:
        (app_dir / "main.py").write_text(
            MAIN_TEMPLATE.format(title=title), encoding="utf-8"
        )
    print(f"Aligned layers for {service_name}")
