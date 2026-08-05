# PlantPilot — Project Plan & Architecture

**Product name:** PlantPilot  
**Tagline:** Self-hosted plant care intelligence — not just a plant inventory.  
**License:** AGPL-3.0 (see Key Decisions)  
**Status:** Design phase — no application code yet  

---

## 1. Vision

PlantPilot is an open-source, self-hosted platform for people who care for plants seriously: houseplant collectors, balcony gardeners, greenhouse hobbyists, and multi-person households. It is **not** a clone of HortusFox.

HortusFox is a capable collaborative plant *inventory* with locations, tasks, chat, and themes. PlantPilot competes by being a **care engine first**: adaptive watering recommendations that improve with feedback, a spatial layout model that matches how people actually arrange plants, a clean API-first architecture that self-hosters and integrators can trust, and a modern React UX that feels fast and accessible.

Someone should choose PlantPilot because:

1. Watering advice is smarter than “every N days.”
2. Multi-user households have real permissions, not just “admin vs user.”
3. The system is designed as a product API with a SPA on top — mobile apps, home automation, and plugins are first-class consumers.
4. Self-hosting is Docker-first with zero paid API keys required for core weather features.
5. The codebase is modular, typed end-to-end, and maintainable.

---

## 2. Competitive Differentiation

| Dimension | HortusFox (inspiration) | PlantPilot (this project) |
|-----------|-------------------------|---------------------------|
| Stack | PHP / Asatru / MariaDB / Vue / Bulma | FastAPI / PostgreSQL / React / Tailwind / shadcn |
| Architecture | Monolithic PHP app + optional REST | REST API first; SPA is a client |
| Watering | Reminders / schedules | Adaptive **Watering Engine** with learning |
| Locations | Flat location list | Hierarchical **Layout Designer** (site → room → shelf → slot) |
| Weather | OpenWeatherMap (API key) | **Open-Meteo** (no key for forecast) |
| Multi-tenancy | Workspace + users | **Households** with RBAC roles |
| Taxonomy | Plant attributes | Species catalog + cultivars + specimen instances |
| History | Logs | Unified **event timeline** |
| Extensibility | Themes + API | Plugin hooks + versioned API + webhooks (later) |
| Chat / inventory | Built-in | **Out of scope v1** — not core care value |

### Deliberate omissions (better UX / focus)

| Requested or common feature | Decision | Why |
|----------------------------|----------|-----|
| Group chat | **Not in v1** | Plant care is task/timeline driven. Chat duplicates Matrix/Signal/Discord. Adds moderation, storage, and mobile complexity for little care value. |
| Full inventory system | **Deferred to v2+** | Fertilizers/tools tracking is useful but secondary to plants, tasks, and watering intelligence. Schema reserved; UI later. |
| Fixed watering schedules as primary model | **Rejected** | Interval reminders train bad habits and ignore season, pot, weather, and plant state. Engine-first; user overrides allowed. |
| OpenWeatherMap | **Rejected for default** | API keys are friction for self-hosters. Open-Meteo is free for non-commercial use and requires no key. Optional providers via plugins later. |
| Theme marketplace like HortusFox | **Simplified** | Light/dark + CSS variables + accent color. Not CSS theme packs. Consistency > novelty. |

---

## 3. Technology Decisions

### 3.1 Frontend

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Framework | **React 19 + TypeScript** | Ecosystem, hiring familiarity, excellent SPA tooling |
| Build | **Vite** | Fast HMR, simple config, first-class TS |
| Styling | **Tailwind CSS v4** | Utility-first, design tokens, dark mode via `class` |
| Components | **shadcn/ui** (Radix primitives) | Accessible, copy-owned components, no heavy UI runtime lock-in |
| Routing | **TanStack Router** or React Router v7 | Prefer TanStack Router if type-safe routes pay off; React Router is fine fallback |
| Data | **TanStack Query** | Cache, retries, optimistic updates for tasks/watering |
| Forms | **React Hook Form + Zod** | Share validation shapes with OpenAPI-generated types where possible |
| DnD (layout) | **@dnd-kit** | Accessible drag-and-drop for layout designer |
| Charts | **Recharts** or **Visx** | Dashboard/statistics; pick one and stick to it |
| i18n | **react-i18next** (phase 2+) | English first; structure strings early |

**Why not Next.js?** Self-hosted plant apps do not need SSR SEO for private dashboards. A static SPA served by nginx/Caddy (or FastAPI static mount) is simpler to operate, cache, and reverse-proxy. API remains the product.

### 3.2 Backend

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Framework | **FastAPI** | Async, OpenAPI auto-docs, Pydantic v2, Python ecosystem for ML later |
| ORM | **SQLAlchemy 2.0** (async) | Mature, explicit, Alembic-friendly |
| Migrations | **Alembic** | Industry standard |
| Validation | **Pydantic v2** | Shared request/response models |
| Auth | **JWT access + refresh tokens** (httpOnly cookies for web preferred; bearer for API clients) | Stateless API scaling; refresh rotation |
| Password hashing | **argon2id** | Modern default over bcrypt |
| Jobs | **ARQ** (Redis) or **APScheduler** in-process for MVP | MVP: APScheduler in API process. Production compose: Redis + ARQ worker when load justifies |
| File storage | **Local filesystem** volume (`/data/media`) | Docker-friendly; S3-compatible adapter interface for later |
| QR | **segno** or **qrcode** + server-side PDF labels | Printable label sheets |
| HTTP client | **httpx** | Open-Meteo, PlantNet |

**Why Python over Node for backend?** Watering engine, future local AI, and scientific helpers fit Python. One language for domain logic + future ML. FastAPI OpenAPI is excellent for the “API first” goal.

### 3.3 Database

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Engine | **PostgreSQL 16+** | JSONB, full-text, arrays, reliability, extensions |
| UUID PKs | **UUIDv7** (time-ordered) where available, else UUIDv4 | Sortable IDs, safe distributed generation |
| Soft delete | Selective | Plants/media: soft-delete. Tasks: hard or soft. Prefer explicit `archived_at` for plants |

**Why not SQLite?** Multi-user households, concurrent writes (photos, tasks, engine recalcs), and JSONB indexing favor Postgres. Self-hosters already run Postgres for many stacks; Compose makes it one service.

### 3.4 Auth & multi-tenancy

- **Users** are global identities (email + password; optional future OIDC).
- **Households** are the tenancy boundary (shared plant collections, layouts, tasks).
- **Memberships** carry roles: `owner`, `admin`, `member`, `viewer`.
- A user may belong to multiple households.
- All plant/layout/task resources are scoped to a household.

**Why households over a single “workspace”?** Real households have multiple gardens or roommates with partial access. Viewers for plant-sitters. Future: greenhouse club sharing a subset of data.

**JWT design:**

- Access token: short-lived (15m), claims: `sub`, `email`, roles per active household optional (prefer re-check membership server-side).
- Refresh token: long-lived (30d), rotated, stored hashed in DB, revocable.
- Web clients: prefer **httpOnly Secure cookies** (CSRF via double-submit or SameSite=Lax + origin checks).
- Programmatic clients: Authorization Bearer.

**Optional later:** reverse-proxy auth headers (Authelia/Authentik) for SSO self-hosters — design headers without building UI in v1.

### 3.5 Deployment

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Caddy/nginx│────▶│  API (uvicorn)│────▶│ PostgreSQL │
│  (optional) │     │  + static SPA │     └────────────┘
└─────────────┘     │  + media vol  │
                    │  + scheduler  │     ┌────────────┐
                    └──────────────┘     │ Redis (opt) │
                                         └────────────┘
```

**Compose services (MVP):**

1. `db` — PostgreSQL  
2. `api` — FastAPI + serves built frontend in production image  
3. `worker` — optional; same image, ARQ/cron mode  

**Dev:** Vite on `:5173` proxying `/api` → FastAPI `:8000`. Hot reload both sides.

**Config:** 12-factor env vars; `.env.example` documented. First-run bootstrap creates admin + household if empty.

### 3.6 Images / media

- Store originals under `/data/media/{household_id}/plants/{plant_id}/...`
- Generate variants: `thumb` (400px), `display` (1600px) with Pillow
- Metadata in DB; files on volume
- Virus scanning: out of scope; max size + MIME allowlist

### 3.7 External integrations

| Integration | Use | Key required? |
|-------------|-----|---------------|
| Open-Meteo | Forecast, humidity, precipitation | No |
| PlantNet | Photo identification | Yes (user/admin provided) |
| Local AI | Future plant ID / health | Optional GPU host |

Integrations are **adapters** behind domain interfaces so providers can swap.

---

## 4. Architecture

### 4.1 Style: modular monolith, clean boundaries

A distributed microservices split is **wrong** for a self-hosted plant app (ops cost, latency, backup complexity). We ship a **modular monolith**:

```
apps/
  api/                 # FastAPI composition root
  web/                 # React SPA
packages/ or backend modules:
  domain/              # Pure business rules (watering engine, permissions)
  application/         # Use cases / services
  infrastructure/      # SQLAlchemy, Open-Meteo, PlantNet, filesystem
  interfaces/          # HTTP routers, schemas, deps
```

**Dependency rule:** `domain` imports nothing from infrastructure. Watering engine is pure Python, unit-testable without DB.

### 4.2 Layers

| Layer | Responsibility |
|-------|----------------|
| **Interface** | HTTP routes, request/response DTOs, auth middleware |
| **Application** | Use cases: “water plant”, “recompute due dates”, “invite member” |
| **Domain** | Entities, value objects, engine algorithms, permission policies |
| **Infrastructure** | ORM models, repositories, external HTTP, file storage |

### 4.3 Core domain modules

| Module | Responsibility |
|--------|----------------|
| `identity` | Users, credentials, tokens |
| `households` | Tenancy, memberships, invites, roles |
| `taxonomy` | Species, cultivars, care profiles (defaults) |
| `plants` | Specimens, attributes, photos, lifecycle status |
| `layout` | Sites, spaces, containers, placements (2D) |
| `timeline` | Append-only care/history events |
| `tasks` | Care tasks, completions, custom reminders |
| `watering` | Engine, factors, recommendations, feedback learning |
| `weather` | Location weather cache, seasonal context |
| `identify` | PlantNet (and future local) identification jobs |
| `labels` | QR generation, printable sheets |
| `stats` | Aggregations for dashboard/analytics |
| `plugins` | Hook registry (v2+) |

### 4.4 Watering Engine (flagship)

**Goal:** Recommend *when* and *how much* (qualitative: light / normal / deep) each plant needs water, never as a static interval alone.

**Inputs (factors):**

| Factor | Source |
|--------|--------|
| Species / cultivar baseline | Taxonomy care profile (drought tolerance, moisture preference) |
| Pot size & material | Plant attributes (volume L, terracotta vs plastic) |
| Soil type | Free-draining / standard / moisture-retentive |
| Plant age / establishment | Acquired date, growth stage |
| Season / photoperiod | Hemisphere + date; optional grow lights flag |
| Indoor vs outdoor | Placement environment |
| Last watering + amount | Timeline events |
| Weather | Open-Meteo: precip, humidity, temp, ET0 if available |
| User feedback | “too wet / just right / too dry” after recommendations |
| Health signals | Optional: yellowing, droop events |

**Algorithm approach (v1 — explainable, not black-box ML):**

1. **Baseline interval** from species care profile (e.g., 5–10 days indoor Monstera, medium pot).
2. **Multiplicative modifiers** (documented, clamped):
   - Pot volume small → shorter interval
   - Terracotta → shorter
   - Winter / low light indoor → longer
   - High outdoor heat + low humidity → shorter
   - Recent rainfall on outdoor plant → extend
3. **Soil moisture proxy score** `S ∈ [0,1]` decaying since last water, modulated by ET-like demand.
4. **Due when** `S < threshold` (species-specific), or user override date.
5. **Learning:** store per-plant `interval_bias` and `threshold_bias` updated by exponential moving average when user marks outcomes. Engine improves per specimen without neural nets.
6. **Confidence** score shown in UI (“low confidence — few waterings logged”).

**Why not pure ML in v1?** Self-hosted users need determinism, debuggability, and zero GPU. EMA learning + factors is “improves over time” without operational risk. Design `WateringEngine` interface so a future model can replace the heuristic backend.

**Recalculation:**

- On plant create/update, watering event, weather refresh, season boundary, feedback submit.
- Nightly batch job recompute for active household plants.
- Cache next_due_at on plant row for fast dashboard queries.

### 4.5 Timeline model

All significant plant actions are **events** in a single append-only (soft-correctable) store:

`watered | fertilized | pruned | repotted | propagated | harvested | relocated | photo_added | note | health_check | identified | custom`

Tasks may *create* events on completion. UI “Timeline” is a query over events (+ system annotations).

**Why not separate tables per action?** Unified query, consistent media attachments, simpler stats, plugin-friendly event types.

### 4.6 Layout Designer

Hierarchical spatial model:

```
Household
  └── Site (Home, Cabin, Allotment)
        └── Space (Living Room, Greenhouse A, Balcony)
              └── Container optional (Shelf 1, Garden Bed North, Grow tent)
                    └── Placement (plant_id + x,y + optional width/height)
```

- Spaces have optional canvas size (px or abstract units).
- Drag-and-drop updates placement coordinates.
- Plants can exist **without** placement (unassigned).
- QR codes deep-link to plant; optional print includes location path.

**Why hierarchy over flat locations?** “Living room / shelf 2 / left” is how humans search and plan watering routes. Flat tags cannot express nesting or 2D arrangement.

### 4.7 Plugin system (design now, implement later)

v1 ships **extension points as interfaces**, not a plugin marketplace:

```python
class WeatherProvider(Protocol):
    async def forecast(self, lat: float, lon: float) -> WeatherSnapshot: ...

class PlantIdentifier(Protocol):
    async def identify(self, image: bytes) -> list[IdentificationCandidate]: ...
```

v2: entry-point discovery (`plantpilot.plugins`), installable packages, webhook emitters on events.

Avoid building a full plugin runtime before core care loops work.

### 4.8 Security baseline

- HTTPS terminated at reverse proxy in production
- CORS restricted to known origins in prod
- Rate limit auth endpoints
- Role checks on every household-scoped route
- Media URLs signed or auth-gated (no public world-readable plant photos by default)
- Secrets only via env
- Dependency scanning in CI later

### 4.9 Accessibility & UX principles

- WCAG 2.2 AA target for core flows
- Keyboard-operable layout (dnd-kit sensors)
- Dark mode default-follow system, user override
- Mobile-first task completion (large tap targets for “I watered this”)
- Empty states that teach (first plant wizard)
- Prefer progressive disclosure over dense admin panels

---

## 5. Repository Structure

```
plantpilot/
├── PROJECT_PLAN.md          # This document
├── SPEC.md                  # Product specification
├── DATABASE.md              # Schema design
├── API.md                   # HTTP API contract
├── ROADMAP.md               # Phased delivery
├── README.md                # (created at scaffold)
├── LICENSE
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── Makefile                 # or just docs; prefer Taskfile/make for DX
│
├── backend/
│   ├── pyproject.toml       # uv or poetry; prefer uv
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py          # FastAPI app factory
│   │   ├── core/            # config, security, logging
│   │   ├── db/              # session, base
│   │   ├── modules/
│   │   │   ├── identity/
│   │   │   ├── households/
│   │   │   ├── taxonomy/
│   │   │   ├── plants/
│   │   │   ├── layout/
│   │   │   ├── timeline/
│   │   │   ├── tasks/
│   │   │   ├── watering/
│   │   │   ├── weather/
│   │   │   ├── identify/
│   │   │   ├── labels/
│   │   │   └── stats/
│   │   └── workers/         # scheduled jobs
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts   # if needed with v4
│   ├── components.json      # shadcn
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app/             # routes, providers
│   │   ├── components/      # ui + domain components
│   │   ├── features/        # feature-sliced UI modules
│   │   ├── lib/             # api client, utils
│   │   └── styles/
│   └── tests/
│
├── deploy/
│   ├── Dockerfile           # multi-stage: build FE + BE
│   ├── Caddyfile.example
│   └── scripts/
│
└── docs/                    # user + contributor docs (later)
```

**Monorepo rationale:** One version, one Compose file, atomic features across API+UI. Not a polyrepo until scale demands it.

---

## 6. Development Workflow

1. Design docs (this phase) — **current**
2. Scaffold repo + Docker + empty health endpoints
3. Auth + households vertical slice
4. Plants + photos + timeline
5. Tasks + dashboard
6. Watering engine v1
7. Weather integration
8. Layout designer
9. QR labels
10. PlantNet identify
11. Statistics polish
12. Hardening, backups docs, release v0.1

**Definition of done for each feature:**

- Migrated schema
- API endpoints + OpenAPI accuracy
- UI path for primary user journey
- Tests for domain logic (engine critical)
- `docker compose up` still works
- No unrelated rewrites

---

## 7. Testing Strategy

| Layer | Tool | Focus |
|-------|------|-------|
| Domain unit | pytest | Watering engine factors, permissions |
| API integration | pytest + httpx AsyncClient | Auth, CRUD, tenancy isolation |
| Frontend unit | Vitest | Pure utils, hooks |
| E2E (later) | Playwright | Login → add plant → water |
| Load (later) | k6 optional | Rare for self-host |

**Tenancy tests are mandatory:** User A must never read household B plants.

---

## 8. Observability & Ops

- Structured JSON logs from API
- `/health` and `/ready` (DB ping)
- Optional Sentry DSN env
- Backup story: `pg_dump` + media volume — document in README
- No phone-home telemetry by default (privacy; optional anonymous version check later, off by default)

---

## 9. Key Decisions (summary)

| # | Decision | Rationale |
|---|----------|-----------|
| K1 | **Name: PlantPilot** | Care guidance positioning, distinct from HortusFox |
| K2 | **Modular monolith, not microservices** | Self-host simplicity |
| K3 | **Household multi-tenancy + RBAC** | Real collaborative care |
| K4 | **Species catalog ≠ plant specimens** | Clean taxonomy vs personal collection |
| K5 | **Unified event timeline** | History, stats, plugins |
| K6 | **Explainable watering engine + EMA learning** | Smart without opaque ML ops |
| K7 | **Open-Meteo default weather** | Zero API key friction |
| K8 | **SPA + REST, not SSR framework** | Private app operational simplicity |
| K9 | **No chat in v1; inventory deferred** | Focus on care differentiators |
| K10 | **AGPL-3.0** | Protects open-source SaaS forks while remaining free for self-hosters; MIT allows closed SaaS without giving back — AGPL is better for community platform health. *If contributors prefer MIT later, discuss — default AGPL.* |
| K11 | **Local media with storage interface** | Simple default, S3-ready later |
| K12 | **Plugin interfaces early, runtime later** | Avoid premature framework |
| K13 | **JWT + refresh rotation; cookie mode for web** | Secure SPA auth without session sticky servers |
| K14 | **UUIDs for public IDs** | Safe exposure in URLs/QR |
| K15 | **English-first UI, i18n-ready strings** | Ship value before localization matrix |

### Alternatives considered

| Topic | Rejected | Why rejected |
|-------|----------|--------------|
| Django monolith | FastAPI | Heavier; OpenAPI/async first-class in FastAPI |
| NestJS + TypeORM | Python stack | Engine/AI affinity |
| GraphQL | REST | Self-hosters and OpenAPI tooling; simpler caching |
| Microservices per module | Modular monolith | Ops burden |
| Fixed watering schedules only | Adaptive engine | Product differentiation |
| Firebase/Supabase hosted | Self-hosted Postgres | Privacy & ownership |
| Electron desktop | Web + PWA later | Self-host web is the category |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Watering engine “feels wrong” | Show factors + confidence; easy user override; feedback loop |
| Scope creep (chat, shop, social) | Ruthless roadmap; core loop first |
| PlantNet rate limits / keys | Optional feature; graceful degrade |
| Photo storage growth | Quotas per household; compression; cleanup of soft-deletes |
| Multi-user permission bugs | Automated tenancy tests |
| Contributor onboarding | Strong docs, `make dev`, Codespaces-friendly later |

---

## 11. Success Metrics (qualitative for OSS)

- New user can Docker-up and log first watering in < 15 minutes
- Watering recommendations change after feedback and weather
- Household of 2 can share plants without shared password
- API alone can power a Home Assistant custom integration (stretch)
- Someone posts “switched from HortusFox for the watering engine”

---

## 12. Document Map

| Document | Contents |
|----------|----------|
| [SPEC.md](./SPEC.md) | Personas, UX, functional requirements |
| [DATABASE.md](./DATABASE.md) | ER model, tables, indexes |
| [API.md](./API.md) | Endpoints, auth, error model |
| [ROADMAP.md](./ROADMAP.md) | Phased implementation order |

---

*Next phase after these docs: scaffold monorepo, Docker Compose, health check, and first vertical slice (auth + household).*
