"""RecentThink Usage Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.usage import router as usage_router
from app.api.internal_admin import router as internal_admin_router
from app.api.exception_handlers import register_exception_handlers
from fastapi import FastAPI

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    yield


app = FastAPI(
    title="RecentThink Usage Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(usage_router)
app.include_router(internal_admin_router)
