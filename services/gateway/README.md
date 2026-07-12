# RecentThink API Gateway

Production reverse-proxy that is the **only public entry point** for RecentThink.
The frontend must call the Gateway (`:8000`) exclusively — never Auth, User, Admin,
AI, or Usage services directly.

The Gateway does **not** implement business logic, access PostgreSQL/Supabase,
validate JWTs, or duplicate service validations. It forwards requests and returns
downstream responses unchanged.

## Architecture

```
Frontend
   │
   ▼
API Gateway (:8000)
   ├── /auth/*, /account/*, /admin/{login,refresh,logout,me}  → Auth   (:8001)
   ├── /profile/*, /users/*                                   → User   (:8002)
   ├── /admin/* (management), /notifications/*                → Admin  (:8003)
   ├── /leetcode/*, /hackerrank/*, /courses/*,
   │   /dsa-pattern/*, /ai/*                                  → AI     (:8004)
   └── /usage/*                                               → Usage  (:8005)
```

Internal service routes (`/internal/admin/*`) are **not** exposed through the Gateway.

## Routing

| Gateway prefix | Downstream | Notes |
|----------------|------------|--------|
| `/auth/*` | Auth | Login, register, refresh, passwords, etc. |
| `/account/*` | Auth | Account status / disable / enable / delete |
| `/admin/login\|refresh\|logout\|me` | Auth | Admin authentication |
| `/admin/*` | Admin | Dashboard, users, analytics, audit, … |
| `/notifications/*` | Admin | User notification polling |
| `/profile/*` | User | Profile CRUD, avatar upload, public profiles |
| `/leetcode/*` | AI | Catch-all |
| `/hackerrank/*` | AI | Catch-all |
| `/courses/*` | AI | Catch-all |
| `/dsa-pattern/*` | AI | Catch-all |
| `/ai/*` | AI | Catch-all |
| `/usage/*` | Usage | Usage recording / queries |
| `GET /` | local | Liveness |
| `GET /health` | local + probes | Aggregated readiness |

## Proxy layer

Reusable `proxy_to_upstream` (`app/proxy/proxy.py`):

1. Accept the incoming FastAPI `Request`
2. Forward method, query params, and raw body (JSON, multipart, files)
3. Forward headers (Authorization, Content-Type, Accept, custom) while stripping hop-by-hop headers
4. Propagate / generate `X-Request-ID`
5. Return the downstream status, headers, and body unchanged
6. Stream when `Accept: text/event-stream` or `?stream=true` (no buffering)
7. Retry transient connect/timeout/`502`/`503`/`504` with exponential backoff
8. Map exhausted failures → `502 Bad Gateway` / `504 Gateway Timeout`

One pooled `httpx.AsyncClient` per upstream is created at startup and stored on
`app.state` — never create a client per request.

## Authentication

The Gateway **does not validate JWT**. It forwards the `Authorization: Bearer …`
header as-is. Downstream services own authentication and authorization.

## Streaming

Long-running AI responses and SSE are supported via `StreamingResponse`.
The Gateway does not buffer streamed bodies.

## Uploads

`multipart/form-data` (profile images, PDFs, documents) is forwarded as the raw
request body with the original `Content-Type` (including boundary).

## Health check

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Liveness — gateway process is up |
| `GET /health` | Readiness — probes Auth, User, Admin, AI, Usage |

`/health` returns gateway status plus each service’s status (`healthy` /
`warning` / `down`) and `response_time_ms`.

## Error handling

| Code | Meaning |
|------|---------|
| `401` / `403` / `404` / `422` | Passed through from downstream |
| `500` | Downstream gateway/service error (passed through) |
| `502` | Downstream unavailable after retries |
| `504` | Downstream read timeout |

## Middleware

- Correlation ID (`X-Request-ID` — reuse client value or generate)
- Request / response access logging + `X-Response-Time` (no secrets logged)
- CORS (explicit origins from env)
- GZip
- Trusted Host (when `GATEWAY_TRUSTED_HOSTS` is not `*`)
- Sentry (when `SENTRY_DSN` is set)

## Environment variables

Service URLs (required for routing; defaults shown for local):

```env
AUTH_SERVICE_URL=http://localhost:8001
USER_SERVICE_URL=http://localhost:8002
ADMIN_SERVICE_URL=http://localhost:8003
AI_SERVICE_URL=http://localhost:8004
USAGE_SERVICE_URL=http://localhost:8005
```

Gateway-specific (optional):

```env
GATEWAY_CONNECT_TIMEOUT=5.0
GATEWAY_READ_TIMEOUT=120.0
GATEWAY_WRITE_TIMEOUT=30.0
GATEWAY_MAX_RETRIES=3
GATEWAY_RETRY_BASE_DELAY_S=0.2
GATEWAY_HEALTH_PROBE_TIMEOUT=2.0
GATEWAY_TRUSTED_HOSTS=*
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

Docker Compose overrides service URLs to container DNS names
(`http://auth_service:8001`, etc.).

## Run locally

```bash
cd services/gateway
uv run uvicorn app.main:app --reload --port 8000
```

Or from repo root: `make run-gateway`.

Frontend:

```env
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000
```

## Tests

```bash
uv run pytest services/gateway/tests -q -o addopts= \
  --cov=services/gateway/app \
  --cov-config=services/gateway/.coveragerc \
  --cov-report=term-missing \
  --cov-fail-under=90
```

Coverage targets proxy forwarding, headers, auth passthrough, uploads,
streaming, retries, CORS, and health aggregation (90%+ on `services/gateway/app`).
