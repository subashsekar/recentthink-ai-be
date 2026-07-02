# Database & Migrations

RecentThink uses **PostgreSQL 16** with **SQLAlchemy 2.x** and **Alembic**.

## Connection

The connection string comes from `DATABASE_URL` (see `.env.example`):

```
postgresql+psycopg://recentthink:recentthink@localhost:5432/recentthink
```

`shared/database/session.py` centralises all database wiring:

- `normalize_database_url()` — upgrades `postgresql://` / `postgres://` DSNs to
  the `postgresql+psycopg://` driver and strips Supabase-style `pgbouncer`
  query params.
- `engine` — created with `pool_pre_ping=True` for resilient pooled
  connections.
- `SessionLocal` — session factory (`autocommit=False`, `autoflush=False`,
  `expire_on_commit=False`).
- `Base` — declarative base whose `MetaData` carries deterministic **naming
  conventions** so constraint/index names are stable and predictable.
- `get_db()` — FastAPI dependency yielding a session and closing it afterwards.

### Naming conventions

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

This produces names like `pk_users`, `uq_admins_email`, keeping Alembic
autogeneration diffs stable across environments.

## Models

ORM models combine the shared `TimestampedModel` (adds timezone-aware
`created_at` / `updated_at`) with the SQLAlchemy `Base`, using SQLAlchemy 2.x
typed `Mapped[...]` / `mapped_column(...)` style:

```python
class User(TimestampedModel, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ...
```

The `User` and `Admin` models currently live in `auth_service`, which owns the
initial migrations.

## Repositories

Data access is encapsulated in repository classes
(`UserRepository`, `AdminRepository`) that:

- accept a `Session` via constructor injection,
- translate SQLAlchemy errors into shared domain exceptions
  (`DuplicateEmailError`, `RecordNotFoundError`, `RepositoryError`),
- log each operation via the shared logger.

## Alembic workflow

The Alembic environment (`migrations/env.py`) imports `Base.metadata` and the
service models as `target_metadata`, and reads the live `DATABASE_URL` from
`shared.config` (the placeholder in `alembic.ini` is never used at runtime).

Common commands (Makefile targets shown; raw commands in parentheses):

| Task | Command |
|-----------------------|-------------------------------------------------|
| Apply all migrations | `make migrate` (`uv run alembic upgrade head`) |
| Roll back one step | `make migrate-down` (`uv run alembic downgrade -1`) |
| Show history | `make migrate-history` (`uv run alembic history --verbose`) |
| Autogenerate revision | `make migrate-revision m="message"` (`uv run alembic revision --autogenerate -m "message"`) |
| Offline SQL preview | `uv run alembic upgrade head --sql` |

### Verified upgrade/downgrade cycle

```bash
uv run alembic upgrade head     # create admins + users, then add profile_image
uv run alembic downgrade -1     # drop profile_image
uv run alembic upgrade head     # re-apply
```

## Seeding

Create the default administrator (idempotent):

```bash
make seed-admin                 # uv run python scripts/seed_admin.py
```

The seed password can be overridden with the `SEED_ADMIN_PASSWORD` environment
variable; change it immediately in real environments.
