# RootCore — REST API Specification

**Style:** REST, JSON, OpenAPI 3 (auto-generated from FastAPI)  
**Base path:** `/api/v1`  
**Related:** [PROJECT_PLAN.md](./PROJECT_PLAN.md) · [SPEC.md](./SPEC.md) · [DATABASE.md](./DATABASE.md)

---

## 1. Design Principles

1. **API first** — the SPA is one client; Home Assistant scripts and CLIs are welcome.
2. **Versioned** — `/api/v1`; breaking changes require `/api/v2`.
3. **Household-scoped resources** — most routes live under `/households/{household_id}/...`.
4. **Predictable errors** — RFC 7807-inspired problem details.
5. **Idempotency** where it matters (task complete, engine upserts).
6. **No GraphQL in v1** — REST + OpenAPI is enough; add GraphQL only if clients demand it.

### Why household in the path?

```
GET /api/v1/households/{hid}/plants
```

vs header `X-Household-Id`: path is explicit, cacheable, and visible in logs/docs. Slightly more verbose; far clearer for multi-household users.

---

## 2. Common Conventions

### 2.1 Content types

- Request: `application/json` unless multipart upload
- Response: `application/json`
- Problem: `application/problem+json` (or JSON body matching shape below)

### 2.2 Authentication

| Mode | Mechanism |
|------|-----------|
| Login | `POST /auth/login` → sets httpOnly cookies **or** returns tokens in body based on `client` field |
| API / mobile | `Authorization: Bearer <access_token>` |
| Web SPA | Cookies: `access_token`, `refresh_token` (Secure, HttpOnly, SameSite=Lax) + CSRF strategy |

**Token lifetimes (defaults):**

- Access: 15 minutes  
- Refresh: 30 days, rotated on use  

**Refresh:** `POST /auth/refresh`  

**Logout:** `POST /auth/logout` (revokes refresh)

### 2.2.1 Login request

```json
{
  "email": "alex@example.com",
  "password": "…",
  "client": "web"
}
```

`client`: `web` → cookies; `api` → JSON tokens.

### 2.3 Pagination

Cursor or offset for lists. **Default: offset pagination** for simplicity in v1; switch hot paths to keyset if needed.

```
GET .../plants?limit=50&offset=0
```

Response envelope:

```json
{
  "items": [ ... ],
  "total": 123,
  "limit": 50,
  "offset": 0
}
```

`limit` max 100.

### 2.4 Filtering & sorting

- Filter: query params (`status=active`, `space_id=`, `q=`)
- Sort: `sort=nickname` or `sort=-next_due_at` (prefix `-` = desc)

### 2.5 Timestamps

ISO-8601 UTC with `Z` suffix, e.g. `2026-07-20T14:30:00Z`.

### 2.6 Error body

```json
{
  "type": "https://rootcore.local/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "pot_size_liters must be > 0",
  "errors": [
    {"loc": ["body", "pot_size_liters"], "msg": "must be > 0", "type": "value_error"}
  ],
  "request_id": "01H…"
}
```

| Status | Use |
|--------|-----|
| 400 | Malformed request |
| 401 | Missing/invalid auth |
| 403 | Authenticated but not allowed |
| 404 | Not found **or** hide cross-tenant existence |
| 409 | Conflict (duplicate membership, etc.) |
| 413 | Upload too large |
| 422 | Validation |
| 429 | Rate limit |
| 500 | Server error |
| 503 | Dependency down (DB) |

**Tenancy:** For resources in another household, return **404** (not 403) to avoid leaking IDs — except when membership is explicit (invite flows).

### 2.7 Idempotency

Optional header `Idempotency-Key` on POSTs that create events/tasks. Stored 24h. Nice-to-have for v1 water logging.

---

## 3. Endpoint Catalog

Legend: **Auth** = requires login; **Role** = minimum household role.

---

### 3.1 System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness |
| GET | `/ready` | No | DB connectivity |
| GET | `/api/v1/meta` | No | Version, registration mode, features |

```json
// GET /api/v1/meta
{
  "name": "RootCore",
  "version": "0.1.0",
  "registration_mode": "invite",
  "features": {
    "plantnet": true,
    "smtp": false
  }
}
```

---

### 3.2 Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | No* | Create user (*if mode allows) |
| POST | `/api/v1/auth/login` | No | Obtain session/tokens |
| POST | `/api/v1/auth/refresh` | Refresh | Rotate tokens |
| POST | `/api/v1/auth/logout` | Auth | Revoke refresh |
| GET | `/api/v1/auth/me` | Auth | Current user profile |
| PATCH | `/api/v1/auth/me` | Auth | Update profile |
| POST | `/api/v1/auth/change-password` | Auth | Change password |
| POST | `/api/v1/auth/forgot-password` | No | Start reset (if SMTP) |
| POST | `/api/v1/auth/reset-password` | No | Complete reset |
| POST | `/api/v1/auth/setup` | No | First-run: create admin + household when user count = 0 |

#### Setup (first run)

```http
POST /api/v1/auth/setup
```

```json
{
  "email": "admin@home.local",
  "password": "…",
  "display_name": "Alex",
  "household_name": "Home",
  "timezone": "Europe/Berlin",
  "latitude": 52.52,
  "longitude": 13.405
}
```

Returns user + household + tokens. **410 Gone** if already initialized.

---

### 3.3 Households

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households` | Auth | List households for current user |
| POST | `/api/v1/households` | Auth | Create household (caller = owner) |
| GET | `/api/v1/households/{hid}` | viewer | Get household |
| PATCH | `/api/v1/households/{hid}` | owner | Update settings/name/location |
| DELETE | `/api/v1/households/{hid}` | owner | Delete household (destructive) |
| GET | `/api/v1/households/{hid}/members` | viewer | List members |
| PATCH | `/api/v1/households/{hid}/members/{user_id}` | admin | Change role |
| DELETE | `/api/v1/households/{hid}/members/{user_id}` | admin | Remove member |
| POST | `/api/v1/households/{hid}/invitations` | admin | Create invite |
| GET | `/api/v1/households/{hid}/invitations` | admin | List invites |
| DELETE | `/api/v1/households/{hid}/invitations/{id}` | admin | Revoke |
| POST | `/api/v1/invitations/accept` | Auth | Accept with token |

---

### 3.4 Taxonomy

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/taxa` | Auth | Search global + optional household custom (`q`, `household_id`) |
| GET | `/api/v1/taxa/{id}` | Auth | Taxon detail + care profile |
| POST | `/api/v1/households/{hid}/taxa` | member | Create custom taxon |
| PATCH | `/api/v1/households/{hid}/taxa/{id}` | member | Update custom only |
| GET | `/api/v1/taxa/{id}/care-profile` | Auth | Care defaults |

Global taxa are read-only via API (seeded). Instance admins may get write routes later.

---

### 3.5 Plants

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/plants` | viewer | List/filter/search |
| POST | `/api/v1/households/{hid}/plants` | member | Create plant |
| GET | `/api/v1/households/{hid}/plants/{pid}` | viewer | Detail + watering_state summary |
| PATCH | `/api/v1/households/{hid}/plants/{pid}` | member | Update |
| POST | `/api/v1/households/{hid}/plants/{pid}/archive` | member* | Archive |
| POST | `/api/v1/households/{hid}/plants/{pid}/decease` | member | Mark deceased |
| DELETE | `/api/v1/households/{hid}/plants/{pid}` | admin | Hard delete (discouraged) |

#### Create plant body

```json
{
  "nickname": "Monstera by the window",
  "taxon_id": "uuid",
  "environment": "indoor",
  "acquired_at": "2024-05-01",
  "pot_size_liters": 5,
  "pot_material": "terracotta",
  "soil_type": "free_draining",
  "growth_stage": "mature",
  "notes": "",
  "tag_names": ["trailing", "pet-safe"],
  "placement": {
    "space_id": "uuid",
    "container_id": null,
    "x": 120,
    "y": 80
  }
}
```

Creating a plant **initializes** `watering_states` and may create an engine watering task.

#### List query params

`q`, `status`, `environment`, `space_id`, `tag`, `urgency`, `sort`, `limit`, `offset`

---

### 3.6 Photos

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/plants/{pid}/photos` | viewer | List |
| POST | `/api/v1/households/{hid}/plants/{pid}/photos` | member | Multipart upload |
| PATCH | `/api/v1/households/{hid}/photos/{photo_id}` | member | Caption / taken_at |
| POST | `/api/v1/households/{hid}/plants/{pid}/photos/{photo_id}/cover` | member | Set cover |
| DELETE | `/api/v1/households/{hid}/photos/{photo_id}` | member | Delete |
| GET | `/api/v1/media/{…}` | Auth | Authenticated media stream |

**Upload:** `multipart/form-data` field `file`; optional `caption`, `taken_at`.

**Media URLs:** Never world-public by default. Options:

1. Same-origin authenticated GET with session cookie  
2. Short-lived signed query token for `<img src>`  

Prefer **signed URLs** (5–15 min) returned in JSON for SPA image tags.

---

### 3.7 Timeline / events

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/events` | viewer | Household feed |
| GET | `/api/v1/households/{hid}/plants/{pid}/events` | viewer | Plant timeline |
| POST | `/api/v1/households/{hid}/events` | member | Create event (note, custom care, etc.) |
| DELETE | `/api/v1/households/{hid}/events/{eid}` | member* | Soft-delete |

#### Log watering (convenience)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/households/{hid}/plants/{pid}/water` | member | Log watering + recompute engine |

```json
{
  "occurred_at": "2026-07-20T09:00:00Z",
  "amount": "normal",
  "volume_ml": 300,
  "notes": null,
  "complete_open_water_task": true
}
```

Response includes created `event` + updated `watering_state`.

#### Feedback

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/households/{hid}/plants/{pid}/watering-feedback` | member | too_dry / ok / too_wet |

```json
{
  "rating": "too_wet",
  "related_event_id": "uuid",
  "notes": "Soil still soggy after 4 days"
}
```

Triggers learning update + recompute.

---

### 3.8 Watering engine

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/plants/{pid}/watering` | viewer | Full recommendation + factors |
| POST | `/api/v1/households/{hid}/plants/{pid}/watering/recompute` | member | Force recompute |
| POST | `/api/v1/households/{hid}/plants/{pid}/watering/pause` | member | Pause until date |
| POST | `/api/v1/households/{hid}/plants/{pid}/watering/resume` | member | Clear pause |
| POST | `/api/v1/households/{hid}/plants/{pid}/watering/override` | member | Set manual next due |
| GET | `/api/v1/households/{hid}/watering/due` | viewer | List due/soon plants |
| POST | `/api/v1/households/{hid}/watering/recompute-all` | admin | Batch recompute |

#### Recommendation response

```json
{
  "plant_id": "…",
  "next_due_at": "2026-07-21T10:00:00Z",
  "urgency": "soon",
  "recommended_amount": "normal",
  "confidence": 0.62,
  "moisture_score": 0.34,
  "last_watered_at": "2026-07-14T09:00:00Z",
  "paused_until": null,
  "manual_next_due_at": null,
  "factors": [
    {
      "key": "species_baseline",
      "label": "Species baseline interval",
      "value": 7.0,
      "unit": "days",
      "effect": "base",
      "detail": null
    }
  ],
  "explanation": "Based on Monstera care profile, pot size, and recent weather."
}
```

---

### 3.9 Tasks

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/tasks` | viewer | List (`status`, `type`, `due_before`, `assignee`) |
| POST | `/api/v1/households/{hid}/tasks` | member | Create |
| GET | `/api/v1/households/{hid}/tasks/{tid}` | viewer | Detail |
| PATCH | `/api/v1/households/{hid}/tasks/{tid}` | member | Update |
| POST | `/api/v1/households/{hid}/tasks/{tid}/complete` | member | Complete (+ optional event) |
| POST | `/api/v1/households/{hid}/tasks/{tid}/reopen` | member | Reopen |
| DELETE | `/api/v1/households/{hid}/tasks/{tid}` | member | Cancel/delete |

#### Complete body

```json
{
  "occurred_at": "2026-07-20T09:15:00Z",
  "result_payload": {
    "amount": "normal"
  }
}
```

---

### 3.10 Calendar

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/calendar` | viewer | `from` & `to` ISO dates → tasks + notable events |
| GET | `/api/v1/households/{hid}/calendar/ical` | token | Optional iCal feed (S) |

---

### 3.11 Layout

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/sites` | viewer | List sites tree optional |
| POST | `/api/v1/households/{hid}/sites` | member | Create site |
| PATCH | `/api/v1/households/{hid}/sites/{sid}` | member | Update |
| DELETE | `/api/v1/households/{hid}/sites/{sid}` | admin | Delete |
| GET | `/api/v1/households/{hid}/sites/{sid}/spaces` | viewer | List spaces |
| POST | `/api/v1/households/{hid}/sites/{sid}/spaces` | member | Create space |
| PATCH | `/api/v1/households/{hid}/spaces/{spid}` | member | Update space/canvas |
| DELETE | `/api/v1/households/{hid}/spaces/{spid}` | admin | Delete |
| POST | `/api/v1/households/{hid}/spaces/{spid}/containers` | member | Create container |
| PATCH | `/api/v1/households/{hid}/containers/{cid}` | member | Update |
| DELETE | `/api/v1/households/{hid}/containers/{cid}` | member | Delete |
| GET | `/api/v1/households/{hid}/spaces/{spid}/placements` | viewer | Plants on canvas |
| PUT | `/api/v1/households/{hid}/plants/{pid}/placement` | member | Upsert placement |
| DELETE | `/api/v1/households/{hid}/plants/{pid}/placement` | member | Unassign |
| POST | `/api/v1/households/{hid}/placements/batch` | member | Batch move (DnD save) |

#### Placement upsert

```json
{
  "space_id": "uuid",
  "container_id": null,
  "x": 240.5,
  "y": 100,
  "width": 64,
  "height": 64
}
```

Emits `relocated` event when space/container changes.

---

### 3.12 Weather

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/weather` | viewer | Current + forecast summary |
| GET | `/api/v1/households/{hid}/sites/{sid}/weather` | viewer | Site-specific |
| POST | `/api/v1/households/{hid}/weather/refresh` | member | Force fetch |

---

### 3.13 Identification

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/households/{hid}/identify` | member | Multipart image → job or sync result |
| GET | `/api/v1/households/{hid}/identify/{job_id}` | member | Poll job |
| POST | `/api/v1/households/{hid}/plants/{pid}/apply-identification` | member | Apply taxon from candidate |

Sync acceptable for PlantNet latency; async job pattern preferred for local AI later.

---

### 3.14 Labels / QR

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/plants/{pid}/label.pdf` | viewer | Single label PDF |
| POST | `/api/v1/households/{hid}/labels/pdf` | viewer | Batch `{ "plant_ids": [] }` → PDF |

Query params: `paper=a4|letter`, `size=small|medium|large`.

---

### 3.15 Statistics

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/stats/summary` | viewer | KPI cards |
| GET | `/api/v1/households/{hid}/stats/watering` | viewer | Water usage series (`from`,`to`) |
| GET | `/api/v1/households/{hid}/stats/tasks` | viewer | Completion rates |
| GET | `/api/v1/households/{hid}/stats/collection` | viewer | Value, distribution, survival |

---

### 3.16 Dashboard

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/dashboard` | viewer | Aggregated today payload |

```json
{
  "tasks_today": [ ... ],
  "attention": [ ... ],
  "weather": { ... },
  "upcoming": [ ... ],
  "recent_events": [ ... ],
  "counts": {
    "plants_active": 42,
    "overdue_water": 3,
    "open_tasks": 8
  }
}
```

Single round-trip for mobile home screen — better than 5 parallel calls on slow NAS Wi-Fi.

---

### 3.17 Tags

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/households/{hid}/tags` | viewer | List |
| POST | `/api/v1/households/{hid}/tags` | member | Create |
| DELETE | `/api/v1/households/{hid}/tags/{id}` | member | Delete |

Plant tags set via plant create/patch `tag_names` (upsert by name).

---

## 4. Resource Shapes (canonical)

### User

```json
{
  "id": "uuid",
  "email": "a@b.c",
  "display_name": "Alex",
  "timezone": "Europe/Berlin",
  "locale": "en",
  "unit_system": "metric",
  "theme": "system",
  "is_instance_admin": false,
  "created_at": "…"
}
```

### Plant (list item)

```json
{
  "id": "uuid",
  "nickname": "Monstera by the window",
  "status": "active",
  "environment": "indoor",
  "taxon": {
    "id": "uuid",
    "scientific_name": "Monstera deliciosa",
    "common_names": ["Swiss cheese plant"]
  },
  "cover_photo": {
    "id": "uuid",
    "thumb_url": "https://…/signed…"
  },
  "placement_path": "Home / Living Room / Shelf 2",
  "watering": {
    "next_due_at": "…",
    "urgency": "due",
    "confidence": 0.7
  },
  "tags": [{"id": "…", "name": "trailing", "color": null}]
}
```

---

## 5. Rate Limiting

| Scope | Default |
|-------|---------|
| Auth login/register | 10 / 15 min / IP |
| Identify | 20 / hour / household (PlantNet cost) |
| General API | 600 / min / user (generous for LAN) |

Return `429` + `Retry-After`.

---

## 6. OpenAPI & Client Generation

- FastAPI exposes `/api/docs` (Swagger), `/api/redoc`, `/api/openapi.json`
- Frontend may use openapi-typescript for types
- Breaking changes require version bump + changelog

---

## 7. Webhooks (v2 sketch — not implemented)

```
POST /api/v1/households/{hid}/webhooks
{
  "url": "https://…",
  "events": ["plant.watered", "task.due"],
  "secret": "…"
}
```

Documented early so event names stay stable.

---

## 8. Security Checklist for Implementers

- [ ] Every household route loads membership and checks role  
- [ ] Plant/photo IDs always filtered by `household_id`  
- [ ] Media signed URLs expire  
- [ ] Passwords argon2id; no password logging  
- [ ] CORS locked in production  
- [ ] SQL only via ORM/parameters  
- [ ] Upload MIME sniff + size cap  
- [ ] Refresh tokens hashed at rest  

---

## 9. Decision Log (API-specific)

| Decision | Choice | Why |
|----------|--------|-----|
| Path-scoped household | `/households/{hid}/…` | Explicit multi-tenant |
| Dashboard aggregate endpoint | Yes | Mobile performance |
| Water convenience endpoint | `POST …/water` | Core loop ergonomics |
| Signed media URLs | Yes | `<img>` without custom headers |
| Problem+JSON errors | Yes | Consistent clients |
| Offset pagination v1 | Yes | Simpler; migrate later |
| Cookie + bearer dual mode | Yes | SPA security + API scripts |
| No public unauthenticated plant API by default | Yes | Privacy |

---

## 10. Example Care Flow (HTTP)

```http
POST /api/v1/auth/login
POST /api/v1/auth/setup          # first run only
GET  /api/v1/households
POST /api/v1/households/{hid}/sites
POST /api/v1/households/{hid}/sites/{sid}/spaces
POST /api/v1/households/{hid}/plants
GET  /api/v1/households/{hid}/dashboard
POST /api/v1/households/{hid}/plants/{pid}/water
POST /api/v1/households/{hid}/plants/{pid}/watering-feedback
GET  /api/v1/households/{hid}/plants/{pid}/watering
```

---

*Implementation generates live OpenAPI from code. This document is the contract; if code and doc diverge, fix code or update this file in the same PR.*
