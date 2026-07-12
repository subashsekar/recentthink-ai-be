# Auth Service — Account Disable & Delete

## Endpoints

Base: Auth Service `:8001` or Gateway `:8000`.

| Method | Path | Auth | Rate limit | Description |
|--------|------|------|------------|-------------|
| GET | `/account/status` | Bearer | — | `{ "is_active", "disabled_at" }` |
| PATCH | `/account/disable` | Bearer | 5/minute | Disable account (password required) |
| DELETE | `/account` | Bearer | 5/minute | Permanently delete (`password` + `confirm: true`) |

### Disable

```http
PATCH /account/disable
Authorization: Bearer <access_token>
Content-Type: application/json

{ "password": "CurrentP@ssw0rd" }
```

Effects: `is_active=false`, `disabled_at=now()`, all refresh tokens revoked.
Login and refresh return **403** with `"Your account has been disabled."`

### Delete

```http
DELETE /account
Authorization: Bearer <access_token>
Content-Type: application/json

{ "password": "CurrentP@ssw0rd", "confirm": true }
```

Returns **204**. Cascades auth tokens + `user_profiles`. Publishes placeholder
`AccountDeleted` event for AI/usage cleanup in other services.

`confirm: false` → **400**.

### Status

```http
GET /account/status
Authorization: Bearer <access_token>
```

## Audit events

Security log (no passwords):

- `user_disabled_account` — `user_id`, `ip`, `user_agent`, `timestamp`
- `user_deleted_account` — same
- `account_deleted_event` — placeholder cross-service hook

## Migration

`o6j1e2f3g4h5_add_user_disabled_deleted_at` adds `users.disabled_at` and
`users.deleted_at`.
