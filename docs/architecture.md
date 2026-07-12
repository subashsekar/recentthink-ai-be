# Architecture

RecentThink is a **microservice** platform organised around **clean
architecture** principles. This document explains the high-level design, the
role of the shared package, and each service's responsibility.

## Principles

- **Separation of concerns** — HTTP delivery, business logic, and data access
  live in distinct layers within every service.
- **Single source of truth** — configuration, database wiring, logging, and
  common models live in `shared/` and are imported (never copied) by services.
- **Dependency inversion** — routes depend on abstractions (repositories,
  service functions) rather than concrete database calls.
- **Independent deployability** — each service is its own FastAPI app with its
  own port and can be built/run/scaled on its own.

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
flow back out as **schemas**. This keeps the framework (FastAPI) at the edges
and the domain logic independent and testable.

## The shared package

`shared/` is an installed, typed (PEP 561, `shared/py.typed`) library reused by
every service:

| Module | Responsibility |
|----------------------|-----------------------------------------------------|
| `config.py` | `Settings` (Pydantic `BaseSettings`), environment/enum types, cached `get_settings()`, and the `SECRET_KEY` safety guard. |
| `database/` | SQLAlchemy `engine`, `SessionLocal`, declarative `Base` (with metadata naming conventions), `get_db()` dependency, and URL normalisation. |
| `models/` | `TimestampedModel` abstract base + `TimestampMixin` (`created_at`/`updated_at`). |
| `schemas/` | Shared Pydantic schemas such as `HealthResponse`. |
| `security/` | Password hashing (`hash_password`, `verify_password`). |
| `exceptions/` | Repository exception hierarchy (`RepositoryError`, `DuplicateEmailError`, `RecordNotFoundError`). |
| `logging/` | `get_logger()` factory honouring `LOG_LEVEL`. |
| `constants/`, `utils/`, `common/` | Reserved namespaces for future shared code. |

Because services import from `shared`, there is exactly one place that knows
how to read configuration or open a database session.

## Service responsibilities

| Service | Port | Phase 1 responsibility | Future |
|-----------------|------|--------------------------------------------|--------------------------|
| `gateway` | 8000 | Entry point / health. | Request routing, edge concerns. |
| `auth_service` | 8001 | Owns User & Admin models, repositories, migrations; DB health check. | Authentication, JWT issuance. |
| `user_service` | 8002 | User profile, avatar, public profile, learning statistics view. | Preferences / notifications. |
| `admin_service` | 8003 | Admin dashboard, user management orchestration, audit logs, notifications (HTTP aggregation only). | Feature flags / reports export. |
| `ai_service` | 8004 | Health only. | AI agents, RAG pipelines. |
| `usage_service` | 8005 | Health only. | Usage metering & billing. |

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
`test`. Local/test tolerate the insecure default `SECRET_KEY` (with a warning);
any other environment **fails fast** if the secret is not overridden. See
[development.md](development.md) for the full workflow.
