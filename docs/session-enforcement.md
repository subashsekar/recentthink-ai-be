# Session enforcement (blocked / deactivated users)

When an administrator **blocks** or **deactivates** a user (or the user
self-disables), refresh tokens are revoked immediately. Access JWTs remain
stateless until expiry, so RecentThink enforces **live user state at the API
Gateway** before traffic reaches User, AI, or Admin services.

## Goals

- Blocked users lose access on the next authenticated request.
- Deactivated / self-disabled users lose access on the next authenticated request.
- Existing JWT issue / refresh / logout flows stay unchanged.
- Frontend APIs stay unchanged (same paths, same Bearer header).

## Architecture

```
Client
  │  Authorization: Bearer <access JWT>
  ▼
API Gateway
  │  1. Skip public credential routes (login, register, refresh, …)
  │  2. If Bearer present:
  │       • verify JWT (sig / exp / iss / aud / token_type)
  │       • GET Auth /internal/auth/user-state/{user_id}
  │         (X-Internal-Service-Token)
  │       • enforce is_active, is_blocked, live role, pwd_ts
  │  3. Forward request + Authorization unchanged
  ▼
User / AI / Admin / Auth (downstream still verify JWT for authorization)
```

Auth Service remains the **single source of truth** for identity. The gateway
does not re-implement login or password logic.

### Auth internal endpoint

```
GET /internal/auth/user-state/{user_id}
Header: X-Internal-Service-Token: <shared secret>

200 {
  "user_id": "...",
  "is_active": true,
  "is_blocked": false,
  "role": "USER",
  "pwd_ts": 1710000000.0
}
```

Auth keeps a short process-local cache of this snapshot and **invalidates it**
on block / unblock / activate / deactivate / self-disable / enable / password
change / delete so the next lookup reflects the mutation immediately.

### Gateway behaviour

| Condition | HTTP | Notes |
|-----------|------|--------|
| No `Authorization` | forward | Downstream returns 401 as today |
| Public path (`/auth/login`, `/auth/refresh`, …) | forward | Allowlist |
| Invalid / expired JWT | 401 | Before upstream |
| `is_blocked` | 403 `ACCOUNT_BLOCKED` | Immediate |
| `is_active == false` | 403 | Immediate |
| JWT `role` ≠ live `role` | 401 | Stale claims |
| JWT `pwd_ts` < live `pwd_ts` | 401 | Password change |
| Auth user-state unavailable | 503 | Fail closed |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `GATEWAY_SESSION_GUARD_ENABLED` | `true` | Master switch (emergency off only) |
| `GATEWAY_USER_STATE_CACHE_TTL_SECONDS` | `0` | Gateway cache of Auth responses; `0` = always ask Auth (immediate) |

Raise the gateway TTL slightly under extreme load only if a few seconds of
post-block access is acceptable. Prefer keeping it at `0` and relying on Auth’s
invalidating in-process cache.

## What did not change

- Access / refresh token formats and lifetimes
- Login, refresh, logout, register contracts
- Downstream JWT claim verification
- Admin block / deactivate public APIs (still revoke refresh tokens)

## Acceptance

- [x] Blocked users cannot call User / AI / Admin via the gateway
- [x] Deactivated users cannot call User / AI / Admin via the gateway
- [x] JWT architecture preserved
- [x] Frontend API paths unchanged
