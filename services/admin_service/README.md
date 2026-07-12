# RecentThink Admin Service

Central **management and aggregation** microservice. Admins authenticate via Auth
Service; this service orchestrates dashboard, user management, analytics, audit
logs, notifications, and system health.

## Ownership boundaries

| Concern | Owner |
|--------|--------|
| Login / JWT / roles / block / unblock / activate / deactivate / delete | **Auth Service** (via internal HTTP) |
| Profiles / learning stats | **User Service** (via internal HTTP) |
| AI sessions / model usage analytics | **AI Service** (via internal HTTP) |
| Request metering analytics | **Usage Service** (via internal HTTP) |
| Audit logs / notifications | **Admin Service** |

Admin Service **never** reads or writes another service's database. All cross-service
access uses `X-Internal-Service-Token` HTTP APIs under `/internal/admin/*`.

## Account states

| Field | Meaning | Who sets it |
|-------|---------|-------------|
| `is_active=false` | Self-disabled (or admin-deactivated) | User (`PATCH /account/disable`) or Admin |
| `is_blocked=true` | Admin force-lock | Admin only |

Login / refresh / protected routes fail if **either** `is_active` is false **or**
`is_blocked` is true. Users re-enable with `POST /account/enable` (email + password).
Blocked users cannot self-enable.

## Architecture

```
Client → Gateway
           ├─ /admin/login|refresh|logout|me → Auth
           ├─ /admin/dashboard|users|…      → Admin
           └─ /notifications                → Admin
                │
                ├─ Auth  /internal/admin/*
                ├─ User  /internal/admin/*
                ├─ AI    /internal/admin/*
                └─ Usage /internal/admin/*
```

## API reference (via Gateway `:8000`)

### Dashboard

- `GET /admin/dashboard` — aggregate identity + profile counters

### Users

- `GET /admin/users` — search / filter / paginate
- `GET /admin/users/{user_id}` — identity + profile + stats + AI history + usage
- `PATCH /admin/users/{user_id}/block|unblock|activate|deactivate`
- `DELETE /admin/users/{user_id}`

### Analytics

- `GET /admin/analytics` — AI sessions / conversations / latency / tokens / cost
- `GET /admin/usage` — requests + top features + provider/model cost
- `GET /admin/models` — provider / model breakdown

### Audit

- `GET /admin/audit-logs` — append-only; no delete API

### System health

- `GET /admin/system-health`

### Notifications (user polling)

- `GET /notifications`
- `PATCH /notifications/{id}/read`
- `PATCH /notifications/read-all`

### Admin broadcast

- `POST /admin/notifications/broadcast`

All `/admin/*` management routes require `ADMIN` or `SUPER_ADMIN` JWT.
Notification polling requires any authenticated user.

## Local run

```bash
make run-admin   # :8003
```

Requires Auth, User, AI, and Usage services for aggregation endpoints.
