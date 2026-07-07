"""RecentThink AI Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.ai import router as ai_router
from app.api.exception_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.agents.leetcode.router import router as leetcode_router
from app.core.config import SERVICE_NAME
from app.core.rate_limit import limiter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.middleware.request_id import RequestIdMiddleware
from shared.monitoring.sentry import init_sentry

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    init_sentry()
    yield


app = FastAPI(
    title="RecentThink AI Service",
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

app.state.limiter = limiter
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(ai_router)
app.include_router(leetcode_router)

app.state.service_name = SERVICE_NAME
