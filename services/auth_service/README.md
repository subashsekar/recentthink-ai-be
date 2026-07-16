# RecentThink Auth Service

Owns identity, credentials, JWT issuance, and account lifecycle.

## Purpose

- Register / login / refresh / logout
- Email verification and password reset
- Account disable / enable / permanent delete
- Admin identity mutations (block, activate, delete) via internal APIs
- Publishes `AccountDeleted` and best-effort purges AI + Usage orphans

## Port

| Mode | Port |
|------|------|
| Local / Docker | **8001** |

## Docs

- Account disable & delete: [ACCOUNT.md](ACCOUNT.md)
- Shared env catalog: [docs/environment.md](../../docs/environment.md)

## Key endpoint groups

| Prefix | Notes |
|--------|--------|
| `/auth/*` | Register, login, refresh, verify, password flows |
| `/account/*` | Status, disable, enable, delete (see ACCOUNT.md) |
| `/admin/login|refresh|logout|me` | Admin authentication |
| `/internal/admin/*` | Admin Service identity APIs (`X-Internal-Service-Token`) |
| `/` / `/health/db` | Liveness + DB check |

Gateway proxies `/auth/*`, `/account/*`, and admin auth paths publicly.

## Env vars

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | PostgreSQL |
| `SECRET_KEY` | JWT signing |
| `INTERNAL_SERVICE_TOKEN` | Internal admin + outbound purge calls |
| `AI_SERVICE_URL` / `USAGE_SERVICE_URL` | AccountDeleted purge targets |
| `EMAIL_*` / `SMTP_*` | Verification and reset mail |
| `SUPER_ADMIN_*` | Optional startup seed |

## Local run

```bash
make run-auth   # :8001
```
