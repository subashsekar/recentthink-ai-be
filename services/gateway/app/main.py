"""RecentThink API Gateway ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
import logging

from app.api.admin_proxy import router as admin_proxy_router
from app.api.ai_proxy import router as ai_proxy_router
from app.api.auth_proxy import router as auth_proxy_router
from app.api.health import router as health_router
from app.api.usage_proxy import router as usage_proxy_router
from app.api.user_proxy import router as user_proxy_router
from app.proxy.client import upstream_client_lifespan
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings
from shared.middleware.request_id import RequestIdMiddleware

APP_VERSION = "0.1.0"
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    cfg = get_settings()
    async with AsyncExitStack() as stack:
        _app.state.ai_client = await stack.enter_async_context(
            upstream_client_lifespan(cfg.ai_service_url),
        )
        _app.state.auth_client = await stack.enter_async_context(
            upstream_client_lifespan(cfg.auth_service_url),
        )
        _app.state.usage_client = await stack.enter_async_context(
            upstream_client_lifespan(cfg.usage_service_url),
        )
        _app.state.user_client = await stack.enter_async_context(
            upstream_client_lifespan(cfg.user_service_url),
        )
        _app.state.admin_client = await stack.enter_async_context(
            upstream_client_lifespan(cfg.admin_service_url),
        )

        # Print all routes on startup for quick verification in deployments.
        routes = []
        for r in _app.router.routes:
            methods = getattr(r, "methods", None)
            path = getattr(r, "path", None)
            name = getattr(r, "name", None)
            if not path:
                continue
            routes.append((path, ",".join(sorted(methods)) if methods else "", name or ""))
        for path, methods, name in sorted(routes):
            logger.info("route path=%s methods=%s name=%s", path, methods, name)

        yield


app = FastAPI(
    title="RecentThink API Gateway",
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
app.include_router(health_router)
app.include_router(auth_proxy_router)
app.include_router(admin_proxy_router)
app.include_router(ai_proxy_router)
app.include_router(usage_proxy_router)
app.include_router(user_proxy_router)
