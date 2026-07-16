# RecentThink Backend

RecentThink is a FastAPI microservice backend for AI-assisted interview and
coding practice. It provides authentication, user profiles, administration,
AI chat, usage tracking, and an API gateway backed by PostgreSQL.

## Services

| Service | Internal port | Purpose |
| --- | ---: | --- |
| Gateway | 8000 | Public entry point |
| Auth | 8001 | Accounts, JWTs, and admin authentication |
| User | 8002 | Profiles and media |
| Admin | 8003 | Administration and analytics |
| AI | 8004 | AI products and streaming chat |
| Usage | 8005 | Usage metering |
| PostgreSQL | 5432 | Persistent data |

Docker publishes the gateway at `http://localhost:8085`. The other application
services remain private to the Docker network.

## Requirements

- Docker Desktop with Docker Compose
- Git
- Optional for local development: Python 3.13 and
  [uv](https://docs.astral.sh/uv/)

## Quick start with Docker

1. Clone the repository and enter it:

   ```powershell
   git clone <repository-url>
   cd recentthink-ai-be
   ```

2. Create your local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Open `.env` and replace every `get-your-*` placeholder with your own value.
   Do not commit `.env`.

4. Build and start the stack:

   ```powershell
   docker compose up --build -d
   ```

5. Confirm that all services are healthy:

   ```powershell
   docker compose ps
   ```

The API is available at:

- Gateway: `http://localhost:8085`
- OpenAPI documentation: `http://localhost:8085/docs`

## Environment configuration

The repository includes:

- `.env.example` — safe template containing placeholders such as
  `get-your-key`
- `.env` — your local secrets; ignored by Git
- `.env.docker` — committed Docker networking defaults with no real secrets

At minimum, replace these values in `.env`:

```env
SECRET_KEY=get-your-key
INTERNAL_SERVICE_TOKEN=get-your-key
OPENROUTER_API_KEY=get-your-key

SUPER_ADMIN_EMAIL=get-your-email
SUPER_ADMIN_PASSWORD=get-your-password
SUPER_ADMIN_FIRST_NAME=get-your-first-name
SUPER_ADMIN_LAST_NAME=get-your-last-name
```

Generate strong random values for `SECRET_KEY` and `INTERNAL_SERVICE_TOKEN`.
Never use `get-your-key` in a deployed environment.

See [`docs/environment.md`](docs/environment.md) for all supported settings.

## Authentication

User endpoints:

- `POST /auth/register`
- `POST /auth/login`

Administrator endpoint:

- `POST /admin/login`

The initial super administrator is created at startup only when all four
`SUPER_ADMIN_*` variables are configured and the database has no existing
super administrator.

Changing `SUPER_ADMIN_PASSWORD` later does not change the password of an
existing account. Account data is stored in the Docker volume, not in Git, so
accounts from another computer do not automatically transfer.

To intentionally remove all local data and seed a fresh administrator:

```powershell
docker compose down -v
docker compose up --build -d
```

Warning: `docker compose down -v` permanently deletes the local PostgreSQL
volume, including all users and application data.

## Useful Docker commands

```powershell
# Follow all logs
docker compose logs -f

# Follow authentication logs
docker compose logs -f auth_service

# Rebuild after pulling changes
docker compose up --build -d

# Stop the stack without deleting data
docker compose down
```

## Local development

Install dependencies:

```powershell
uv sync --all-groups
```

Run individual services:

```powershell
make run-gateway
make run-auth
make run-user
make run-admin
make run-ai
make run-usage
```

Run checks:

```powershell
make lint
make typecheck
make test
```

## Documentation

- [Architecture](docs/architecture.md)
- [Docker](docs/docker.md)
- [Environment variables](docs/environment.md)
- [Database](docs/database.md)
- [Development](docs/development.md)
- [Testing](docs/testing.md)

## Security

- Never commit `.env`, API keys, passwords, or tokens.
- Use unique, randomly generated secrets outside local development.
- Expose only the gateway publicly.
- Rotate any credential that has been shared or committed.
