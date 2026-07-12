# RecentThink User Service

Production-ready **user profile** microservice. Owns profile presentation, avatars,
coding-platform handles, and public profiles. Authentication remains exclusively
in Auth Service.

## Ownership boundaries

| Concern | Owner |
|---------|--------|
| Register / login / JWT / refresh / password / email verification / roles | **Auth Service** |
| Profile fields, avatar URL, platform usernames, public profile, learning stats view | **User Service** |

User Service verifies JWTs locally (same `SECRET_KEY` as Auth) via claims-only
`AuthenticatedUser` — it does **not** re-implement login, token issuance, or RBAC
storage.

## Architecture

```
Client
  │
  ▼
API Gateway  (/profile/*)
  │
  ▼
User Service
  ├── ProfileService          (CRUD + owner/admin RBAC)
  ├── AvatarService           (upload / replace / delete via shared storage)
  ├── StatisticsService       (read-only aggregates from AI tables)
  └── PublicProfileService    (safe public subset)
        │
        ▼
  ProfileRepository / StatisticsRepository
        │
        ▼
  PostgreSQL  (user_profiles + AI progress tables)
```

## Database schema

### `user_profiles`

| Column | Notes |
|--------|--------|
| `id` | UUID PK |
| `user_id` | UUID FK → `users.id` (CASCADE), unique |
| `username` | Public handle (unique, optional until set) |
| `first_name`, `last_name` | Display names |
| `mobile_number` | Private |
| `profile_picture_url` | URL only — binary in object storage |
| `bio` | Max 500 chars |
| `current_status` | Enum string |
| `college`, `company`, `current_role`, `experience_years` | Professional details |
| `primary_skill` | Enum string |
| `leetcode_username`, `hackerrank_username`, `github_username` | Normalized handles |
| `linkedin_url`, `portfolio_url` | Validated http(s) URLs |
| `created_at`, `updated_at` | Timestamps |

`username` is required for a public profile URL. It is not an auth identity field.

### Enums

**Current status:** Student, Working Professional, Job Seeker, Freelancer, Career Switcher, Other

**Primary skill:** Python, Java, JavaScript, C++, Go, Rust, AI/ML, Backend, Frontend, Full Stack, Data Science

### Statistics (read-only)

`StatisticsRepository` aggregates existing AI-owned tables — **no duplicated counters**:

- `leetcode_progress` + `hackerrank_progress` → problems solved / streaks
- `course_progress` → courses completed / study hours / streaks
- `pattern_progress` → patterns learned / learning time / streaks

## API reference

Base URL (direct): `http://localhost:8002`  
Via gateway: `http://localhost:8000`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profile` | Bearer | Current user's full profile. Admins: `?user_id=` |
| PATCH | `/profile` | Bearer | Update profile (creates on first update). Admins: `?user_id=` |
| GET | `/profile/statistics` | Bearer | Learning statistics |
| POST | `/profile/avatar` | Bearer | Upload/replace avatar (`multipart/form-data` file) |
| DELETE | `/profile/avatar` | Bearer | Delete avatar |
| GET | `/profile/public/{username}` | Public | Safe public profile + statistics |

### Public profile never exposes

Email, mobile number, internal IDs (`id` / `user_id`), JWT claims, or roles.

## Validation rules

- Trim whitespace; blank → `null`
- Bio ≤ 500 characters
- Mobile: E.164-ish (`+` optional, 8–15 digits)
- LinkedIn: `http(s)` host on `linkedin.com`
- Portfolio: absolute `http`/`https` URL
- Platform usernames: strip leading `@`, lowercase, alphanumeric/`_`/`-`
- Public username: 3–30 chars, `[a-z0-9_]`, stored lowercase
- Avatar: JPEG / PNG / WebP / GIF, max 2 MiB, secure UUID filename

## Authorization

| Actor | Capabilities |
|-------|----------------|
| User | Read/update own profile, avatar, statistics |
| Admin / Super Admin | Read/update any profile via `?user_id=` |
| Anonymous | Public profile only |

## Storage

Uses `shared.storage`. Default for local development is the filesystem; for
deployed websites use **Supabase Storage**.

### Local (development)

```env
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=storage
STORAGE_PUBLIC_BASE_URL=http://localhost:8002/media
```

Files land under `storage/avatars/...` and are served at `/media/...`.

### Supabase (production / website)

Bucket name used by this project: **`recenthink_user_profile_picture`**
(must be **Public** so profile images load in the browser).

```env
STORAGE_BACKEND=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_STORAGE_BUCKET=recenthink_user_profile_picture
# Optional — auto-derived from SUPABASE_URL + bucket when omitted / left as local default:
# STORAGE_PUBLIC_BASE_URL=https://<project-ref>.supabase.co/storage/v1/object/public/recenthink_user_profile_picture
```

Upload flow: `POST /profile/avatar` → Supabase bucket → DB stores only the
public URL (`profile_picture_url`). Never put the service-role key in the
frontend.

Also: `AVATAR_MAX_BYTES`, `AVATAR_ALLOWED_CONTENT_TYPES`

## Running

```bash
# from repo root
uv run uvicorn app.main:app --app-dir services/user_service --reload --port 8002
make migrate   # applies n5i0d1e2f3g4_add_user_profiles
```

## Tests

```bash
uv run pytest services/user_service/tests -q --cov=services/user_service/app --cov=shared/storage --cov-report=term-missing
```
