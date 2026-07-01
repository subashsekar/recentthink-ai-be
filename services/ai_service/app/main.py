"""RecentThink AI Service ASGI application entry point."""

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
    title="RecentThink AI Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(health_router)
