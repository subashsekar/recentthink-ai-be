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

## Model base classes & mixins

`shared/models/` provides two reusable, abstract bases (SQLAlchemy 2.x typed
`Mapped[...]` / `mapped_column(...)` style):

| Base / mixin | Columns added | Use for |
|--------------------|-------------------------------|-----------------------------------|
| `CreatedAtMixin` / `CreatedAtModel` | `created_at` | Insert-only rows (e.g. one-time tokens) |
| `TimestampMixin` / `TimestampedModel` | `created_at` + `updated_at` | Mutable entities (users, admins) |

`TimestampMixin` extends `CreatedAtMixin`, so there is a single definition of
`created_at`.

```python
class User(TimestampedModel, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ...

class RefreshToken(CreatedAtModel, Base):
    __tablename__ = "refresh_tokens"
    ...
```

## Authentication schema (`auth_service`)

`auth_service` owns the migrations and the following tables:

| Table | Purpose | Key columns |
|-------------------------------|--------------------------------------|-----------------------------------------------|
| `users` | Identity/credentials | `id` (UUID PK), `email` (unique), `password_hash`, `role`, `is_verified`, `is_active` |
| `admins` | Administrator accounts | `id` (UUID PK), `email` (unique), ... |
| `refresh_tokens` | Long-lived session tokens | FK `user_id` (CASCADE, indexed), `token` (indexed), `expires_at`, `is_revoked` |
| `email_verification_tokens` | One-time email confirmation | FK `user_id` (CASCADE, indexed), `token` (unique), `expires_at`, `is_used` |
| `password_reset_tokens` | One-time password reset | FK `user_id` (CASCADE, indexed), `token` (unique), `expires_at`, `is_used` |

`role` is stored as a non-native enum (`VARCHAR(50)`) from the reusable
`Role` enum (`SUPER_ADMIN`, `ADMIN`, `USER`; default `USER`). Each token table
has an index on its `user_id` foreign key for fast per-user lookups. `email`
relies on the unique constraint's implicit index (no separate `index=True`).

Deleting a `User` cascades to all related token rows via
`relationship(cascade="all, delete-orphan")` on the ORM side and
`ON DELETE CASCADE` on the database foreign keys.

## Schemas: DB layer vs. API layer

Schemas are split so credential material is never serialized to clients:

- **Database-layer** (`app/schemas/user.py`, `refresh_token.py`) — model the
  repository boundary. `UserCreate`/`UserUpdate` carry `password_hash`;
  `UserRead` deliberately **excludes** it.
- **API-facing** (`app/schemas/responses.py`) — `UserResponse`,
  `CurrentUserResponse`, `LoginResponse`. These are the only schemas returned
  from HTTP endpoints and never expose `password_hash`.

## Repositories

Data access is encapsulated in repository classes (`UserRepository`,
`AdminRepository`, `RefreshTokenRepository`, `EmailVerificationRepository`,
`PasswordResetRepository`) that:

- accept a `Session` via constructor injection,
- expose only database operations (no business logic),
- translate SQLAlchemy errors into shared domain exceptions
  (`DuplicateEmailError`, `RecordNotFoundError`, `RepositoryError`),
- log each operation via the shared logger.

`UserRepository.update_user()` only writes whitelisted columns
(`UserRepository.EDITABLE_FIELDS`); unknown keys raise `ValueError`.
`RefreshTokenRepository` additionally provides `get_active_refresh_tokens()`,
`revoke_all_tokens()`, and `delete_expired_tokens()` for session management.

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

The full cycle is exercised in CI (see `.github/workflows/ci.yml`) so every
revision's `downgrade()` is validated on each push:

```bash
uv run alembic upgrade head      # apply all revisions
uv run alembic downgrade base    # roll every revision back
uv run alembic upgrade head      # re-apply, leaving the schema at head
```

## Seeding

Create the default administrator (idempotent):

```bash
make seed-admin                 # uv run python scripts/seed_admin.py
```

The seed password can be overridden with the `SEED_ADMIN_PASSWORD` environment
variable; change it immediately in real environments.
