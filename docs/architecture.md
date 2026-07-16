# Architecture

RecentThink is a **microservice** portfolio AI platform organised around
**clean architecture**. This document summarises service roles and delivery
status — not a Phase 1 skeleton.

## Principles

- **Separation of concerns** — HTTP delivery, business logic, and data access
  live in distinct layers within every service.
- **Single source of truth** — configuration, database wiring, logging, and
  common models live in `shared/` and are imported (never copied) by services.
- **Dependency inversion** — routes depend on abstractions (repositories,
  service functions) rather than concrete database calls.
- **Independent deployability** — each service is its own FastAPI app with its
  own port and can be built/run/scaled on its own.
- **No shared DB writes across services** — Admin aggregates via
  `X-Internal-Service-Token` HTTP (`/internal/admin/*`); Auth owns identity,
  AI owns sessions/progress, Usage owns metering.

## Layout of a service

Every service under `services/<name>/` has the same internal shape:

```
app/
├── api/            # HTTP routes (delivery layer)
├── services/       # Use-case / business logic
├── repositories/   # Data access (SQLAlchemy sessions & queries)
├── models/         # ORM entities
├── schemas/        # Pydantic request/response models
├── core/           # Service-local config (SERVICE_NAME, PORT)
├── dependencies/   # FastAPI dependency providers
├── middleware/     # Cross-cutting HTTP middleware
├── utils/          # Helpers
└── main.py         # FastAPI app + lifespan + router registration
tests/              # Service-scoped tests
```

A request flows **api → services → repositories → models/DB**, and results
flow back out as **schemas**.

## The shared package

`shared/` is an installed, typed (PEP 561, `shared/py.typed`) library reused by
every service:

| Module | Responsibility |
|----------------------|-----------------------------------------------------|
| `config.py` | `Settings` (Pydantic `BaseSettings`), env enums, cached `get_settings()`, secret/token guards. |
| `database/` | SQLAlchemy `engine`, `SessionLocal`, `Base`, `get_db()`. |
| `models/` | `TimestampedModel` / `CreatedAtModel` mixins. |
| `schemas/` | Shared Pydantic schemas such as `HealthResponse`. |
| `security/` | Passwords, JWT helpers, internal service token. |
| `exceptions/` | Domain exception hierarchy. |
| `logging/` | `get_logger()` factory honouring `LOG_LEVEL`. |

## Service responsibilities

| Service | Port | Status | Responsibility |
|-----------------|------|--------|----------------|
| `gateway` | 8000 | **Done** | Public reverse proxy; JWT + live user-state session guard; SSE passthrough for `/chat/*`. |
| `auth_service` | 8001 | **Done** | Register/login, JWT + refresh, email verify/reset, account disable/delete, admin identity mutations, internal admin + user-state APIs. |
| `user_service` | 8002 | **Done** | Profiles, avatars (local/Supabase), public profile/search, profile completion, learning-stats reads. |
| `admin_service` | 8003 | **Done** | Dashboard, user management, usage/AI analytics aggregation, audit logs, notifications, feature flags, system health. |
| `ai_service` | 8004 | **Done (~95%)** | LeetCode / HackerRank / Course Generator / DSA Pattern Coach; shared LangGraph + one OpenRouter call; chat SSE; cache; usage; internal purge. See [AI_SERVICE_COMPLETION_REPORT.md](AI_SERVICE_COMPLETION_REPORT.md). |
| `usage_service` | 8005 | **Done** | Usage metering (`usage_records`), admin analytics APIs, internal purge. |

### Product / feature status

| Feature | Status |
|---------|--------|
| LeetCode Mentor | **Done** |
| HackerRank Mentor | **Done** |
| DSA Pattern Coach | **Done** |
| Course Generator | **Done** |
| Chat / SSE streaming (`/chat/{feature}/*`) | **Done** |
| Feature flags (Admin) | **Done** |
| Account delete → AI/Usage orphan cleanup | **Done** |
| Gateway session enforcement (block / deactivate) | **Done** — see [session-enforcement.md](session-enforcement.md) |
| Interview Trainer | **Out of Scope** (not implemented) |
| Quotas / billing invoices | Deferred |
| K8s / Terraform / Helm / Prometheus / Grafana / OTel | Deferred (placeholders only) |

## Health endpoints

Every service exposes a uniform liveness endpoint:

```
GET /  ->  200  {"service": "<name>", "status": "healthy"}
```

Services with extra dependency checks expose them under `/health/*`. For
example, the Auth Service verifies database connectivity at:

```
GET /health/db  ->  200  {"message": "Database Connected Successfully"}
```

## Configuration & environments

`Settings` supports `local`, `development`, `staging`, `production`, and
`test`. Local/test tolerate insecure default `SECRET_KEY` /
`INTERNAL_SERVICE_TOKEN` (with a warning); any other environment **fails
fast** if those are not overridden. See [environment.md](environment.md) and
[development.md](development.md).
