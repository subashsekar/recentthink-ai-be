# Environment variables

Single catalog of key settings from `shared/config.py`. Values load from real
environment variables, then the repo-root `.env`. Docker Compose also applies
`.env.docker` for in-network hostnames. Never commit real secrets.

| Variable | Purpose |
|----------------------------------|--------------------------------------------------|
| `ENVIRONMENT` | `local` / `development` / `staging` / `production` / `test` |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, …) |
| `DATABASE_URL` | PostgreSQL DSN (`postgresql+psycopg://…`) |
| `SECRET_KEY` | JWT signing secret (required outside local/test) |
| `JWT_ALGORITHM` | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Token `iss` / `aud` claims |
| `RATE_LIMIT_ENABLED` | Auth endpoint throttling toggle |
| `RATE_LIMIT_LOGIN` / `REGISTER` / `ACCOUNT` / `RESEND_VERIFICATION` | slowapi limit strings |
| `SUPER_ADMIN_EMAIL` / `PASSWORD` / `FIRST_NAME` / `LAST_NAME` | Startup seed (all four required) |
| `EMAIL_PROVIDER` | `console` (default) or `smtp` |
| `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME` / `EMAIL_SUPPORT_ADDRESS` | Envelope / branding |
| `EMAIL_VERIFICATION_URL` | Frontend verify URL (token query param) |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | Verification token TTL |
| `PASSWORD_RESET_URL` | Frontend reset URL |
| `PASSWORD_RESET_TOKEN_EXPIRE_HOURS` | Reset token TTL |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP transport |
| `SMTP_USE_TLS` / `SMTP_TIMEOUT_SECONDS` | SMTP options |
| `CORS_ORIGINS` | Comma-separated origins (no `*`) |
| `CORS_ALLOW_CREDENTIALS` / `METHODS` / `HEADERS` | CORS policy |
| `SENTRY_DSN` / `SENTRY_ENVIRONMENT` / `SENTRY_RELEASE` / `SENTRY_TRACES_SAMPLE_RATE` | Optional Sentry |
| `OPENROUTER_API_KEY` | OpenRouter key (AI Service) |
| `OPENROUTER_BASE_URL` | Default `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | Default chat model id |
| `OPENROUTER_TIMEOUT_SECONDS` | Upstream timeout |
| `OPENAI_API_KEY` / `GOOGLE_API_KEY` | Reserved / optional |
| `STORAGE_BACKEND` | `local` or `supabase` |
| `STORAGE_LOCAL_PATH` / `STORAGE_PUBLIC_BASE_URL` | Local avatar storage |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_STORAGE_BUCKET` | Supabase storage |
| `AVATAR_MAX_BYTES` / `AVATAR_ALLOWED_CONTENT_TYPES` | Upload limits |
| `AUTH_SERVICE_URL` | Auth base URL (Docker: `http://auth_service:8001`) |
| `USER_SERVICE_URL` | User base URL |
| `ADMIN_SERVICE_URL` | Admin base URL |
| `AI_SERVICE_URL` | AI base URL |
| `USAGE_SERVICE_URL` | Usage base URL |
| `INTERNAL_SERVICE_TOKEN` | Shared service-to-service secret |
| `GATEWAY_SESSION_GUARD_ENABLED` | Gateway live user-state check (`true` by default) |
| `GATEWAY_USER_STATE_CACHE_TTL_SECONDS` | Optional gateway cache of Auth user-state (`0` = immediate) |

Outside local/test, insecure defaults for `SECRET_KEY` and
`INTERNAL_SERVICE_TOKEN` cause startup failure.

Session enforcement (blocked / deactivated users) is documented in
[session-enforcement.md](session-enforcement.md).
