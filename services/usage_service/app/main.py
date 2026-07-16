"""RecentThink Usage Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.usage import router as usage_router
from app.api.internal_admin import router as internal_admin_router
from app.api.exception_handlers import register_exception_handlers
from app.core.config import SERVICE_NAME
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.middleware.request_id import RequestIdMiddleware
from shared.monitoring.sentry import init_sentry

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    init_sentry()
    yield


app = FastAPI(
    title="RecentThink Usage Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)

_cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg.cors_origins,
    allow_credentials=_cfg.cors_allow_credentials,
    allow_methods=_cfg.cors_allow_methods,
    allow_headers=_cfg.cors_allow_headers,
    expose_headers=["X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(usage_router)
app.include_router(internal_admin_router)

app.state.service_name = SERVICE_NAME
