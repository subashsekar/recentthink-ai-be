# RecentThink Usage Service

Meters AI and platform usage for analytics and admin dashboards.

## Purpose

- Accept internal `POST /usage/record` writes from AI Service
- Aggregate tokens, cost, features, models, providers for Admin
- Best-effort purge on account delete (`DELETE /internal/admin/users/{user_id}`)

## Port

| Mode | Port |
|------|------|
| Local / Docker | **8005** |

## Key endpoints

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/` | — | Health |
| POST | `/usage/record` | `X-Internal-Service-Token` | Create metering row |
| GET | `/internal/admin/analytics/*` | Internal token | Dashboard, tokens, features, … |
| GET | `/internal/admin/users/{user_id}` | Internal token | Recent raw records |
| DELETE | `/internal/admin/users/{user_id}` | Internal token | Purge `usage_records` |

Not exposed through the Gateway for internal admin routes. Public clients use
Admin Service analytics via Gateway `/admin/analytics/*`.

## Env vars

Uses `shared/config.py`. Critical:

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | PostgreSQL |
| `INTERNAL_SERVICE_TOKEN` | Required for `/usage/record` and `/internal/admin/*` |
| `USAGE_SERVICE_URL` | Used by other services to reach this one |

See [docs/environment.md](../../docs/environment.md).

## Local run

```bash
make run-usage   # :8005
```
