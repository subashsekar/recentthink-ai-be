"""RecentThink API Gateway ASGI application entry point.

The gateway is the only public entry point. It reverse-proxies to Auth, User,
Admin, AI, and Usage services without implementing business logic.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings
from shared.logging.logger import get_logger
from shared.middleware.request_id import RequestIdMiddleware
from shared.monitoring.sentry import init_sentry
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.account_proxy import router as account_proxy_router
from app.api.admin_proxy import router as admin_proxy_router
from app.api.ai_proxy import router as ai_proxy_router
from app.api.auth_proxy import router as auth_proxy_router
from app.api.health import router as health_router
from app.api.notifications_proxy import router as notifications_proxy_router
from app.api.usage_proxy import router as usage_proxy_router
from app.api.user_proxy import router as user_proxy_router
from app.core.config import APP_VERSION, SERVICE_NAME, TRUSTED_HOSTS
from app.middleware.timing import RequestTimingMiddleware
from app.proxy.client import upstream_client_lifespan

logger = get_logger("gateway")


def should_enable_trusted_host(hosts: list[str]) -> bool:
    """Return True when TrustedHostMiddleware should be enabled."""
    return hosts != ["*"]


def configure_trusted_host(
    application: FastAPI,
    hosts: list[str] | None = None,
) -> None:
    """Attach TrustedHostMiddleware when hosts are explicitly configured."""
    resolved = TRUSTED_HOSTS if hosts is None else hosts
    if should_enable_trusted_host(resolved):
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=resolved)


def _log_startup(app: FastAPI) -> None:
    cfg = get_settings()
    logger.info(
        "startup service=%s version=%s environment=%s",
        SERVICE_NAME,
        APP_VERSION,
        cfg.environment.value,
    )
    logger.info(
        "loaded_services auth=%s user=%s admin=%s ai=%s usage=%s",
        cfg.auth_service_url,
        cfg.user_service_url,
        cfg.admin_service_url,
        cfg.ai_service_url,
        cfg.usage_service_url,
    )

    routes: list[tuple[str, str, str]] = []
    for r in app.router.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", None)
        name = getattr(r, "name", None)
        if not path:
            continue
        routes.append((path, ",".join(sorted(methods)) if methods else "", name or ""))
    logger.info("registered_routes count=%s", len(routes))
    for path, methods, name in sorted(routes):
        logger.info("route path=%s methods=%s name=%s", path, methods, name)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: pooled upstream clients + startup banner."""
    init_sentry()
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
        _log_startup(_app)
        yield


app = FastAPI(
    title="RecentThink API Gateway",
    version=APP_VERSION,
    description=(
        "Public reverse-proxy entry point for RecentThink. "
        "Forwards requests to Auth, User, Admin, AI, and Usage services."
    ),
    lifespan=lifespan,
)

# Middleware order: last added runs first (outermost).
# TrustedHost → CORS → GZip → RequestId → Timing → routes
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

get_settings.cache_clear()
_cfg = get_settings()
logger.info("cors_origins=%s", _cfg.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg.cors_origins,
    allow_credentials=_cfg.cors_allow_credentials,
    allow_methods=_cfg.cors_allow_methods,
    allow_headers=["*"] if _cfg.is_local else _cfg.cors_allow_headers,
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

configure_trusted_host(app)

app.include_router(health_router)
app.include_router(auth_proxy_router)
app.include_router(account_proxy_router)
app.include_router(admin_proxy_router)
app.include_router(notifications_proxy_router)
app.include_router(ai_proxy_router)
app.include_router(usage_proxy_router)
app.include_router(user_proxy_router)

app.state.service_name = SERVICE_NAME
