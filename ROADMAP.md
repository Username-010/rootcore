# PlantPilot — Implementation Roadmap

**Related:** [PROJECT_PLAN.md](./PROJECT_PLAN.md) · [SPEC.md](./SPEC.md) · [DATABASE.md](./DATABASE.md) · [API.md](./API.md)

---

## 1. Delivery Philosophy

1. **Runnable at all times** — after every milestone, `docker compose up` yields a working app (even if features are incomplete).
2. **Vertical slices** — ship UI + API + DB together for each capability; no backend-only deserts.
3. **Engine is a product pillar** — do not postpone watering intelligence behind cosmetic polish.
4. **No placeholder fake features** — if a button exists, it works or is hidden.
5. **Tests for tenancy and engine** — non-negotiable as those modules land.
6. **Never rewrite unrelated code** — incremental, focused PRs.

### Definition of Done (every feature)

- [ ] Schema migrated (if needed)  
- [ ] API endpoints documented in OpenAPI  
- [ ] Primary UI path works  
- [ ] Builds clean (backend + frontend)  
- [ ] Relevant tests pass  
- [ ] Compose stack healthy  

---

## 2. Phase Overview

| Phase | Name | Outcome |
|-------|------|---------|
| **0** | Design | Docs complete ← **you are here** |
| **1** | Foundation | Repo, Docker, CI skeleton, health |
| **2** | Identity & households | Login, setup, multi-user tenancy |
| **3** | Plants & media | Collection CRUD, photos, taxonomy seed |
| **4** | Timeline & tasks | Events, manual tasks, dashboard shell |
| **5** | Watering engine v1 | Factors, due list, feedback learning |
| **6** | Weather | Open-Meteo + engine coupling |
| **7** | Layout designer | Sites/spaces/placements + DnD |
| **8** | Calendar, QR, stats | Care surface completeness |
| **9** | Identification | PlantNet integration |
| **10** | Polish & v0.1 | PWA shell, docs, hardening, release |

Phases 5–6 are the **differentiation core**. Do not skip ahead to QR cosmetics before the engine works.

---

## 3. Phase 0 — Design (current)

**Deliverables:**

- [x] `PROJECT_PLAN.md`
- [x] `SPEC.md`
- [x] `DATABASE.md`
- [x] `API.md`
- [x] `ROADMAP.md`

**Exit criteria:** Architecture decisions recorded; no application code required yet.

---

## 4. Phase 1 — Foundation ✅

**Goal:** Empty but professional monorepo that runs in Docker.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] Initialize git repo + `LICENSE` (AGPL-3.0) + root `README.md`
2. [x] Backend: FastAPI app factory, settings via pydantic-settings, `/health` `/ready`
3. [x] Frontend: Vite + React + TS + Tailwind + shadcn baseline, dark mode toggle stub
4. [x] `docker-compose.yml`: `db`, `api` (dev mounts optional)
5. [x] `docker-compose.dev.yml` or documented dev workflow (Vite + uvicorn reload)
6. [x] `.env.example`
7. [x] Alembic wired with empty migration baseline
8. [x] Makefile/task targets: `dev`, `test`, `lint`, `migrate`
9. [x] Lint tooling: ruff + eslint (pre-commit optional later)

### Runnable check

- [x] Postgres via Compose/Podman healthy
- [x] API returns `{"status":"ok"}` on `/health`; `/ready` reports database
- [x] Frontend builds; shell shows system status + dark mode

### Tests

- [x] Health + meta endpoint tests
- [x] Frontend util unit tests

---

## 5. Phase 2 — Identity & Households ✅

**Goal:** Secure multi-user tenancy.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] Tables: `users`, `refresh_tokens`, `households`, `memberships`, `invitations`
2. [x] Auth: register (mode-aware), login, refresh, logout, me, change-password
3. [x] First-run `POST /auth/setup`
4. [x] Household CRUD + members + invites
5. [x] Frontend: setup wizard, login, household switcher shell, auth-gated layout
6. [x] Permission dependency helpers (`require_household_role`)

### Runnable check

- [x] Fresh install → setup wizard → second user invited → both see household

### Tests

- [x] Auth happy path  
- [x] Cross-household 404 isolation  
- [x] Role forbidden paths  

---

## 6. Phase 3 — Plants, Taxonomy & Photos ✅

**Goal:** Real collection management.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] Tables: `taxa`, `care_profiles`, `plants`, `tags`, `plant_tags`, `plant_photos`
2. [x] Seed common houseplant taxa + care profiles (JSON seed)
3. [x] Plant CRUD, search, tags, archive/decease
4. [x] Photo upload, variants, signed URLs, cover photo
5. [x] Frontend: plant list, plant detail, add/edit plant, photo gallery
6. [x] Taxon autocomplete

### Runnable check

- [x] Add plants with photos; search finds them; detail shows species

### Tests

- [x] Plant list filters  
- [x] Media auth (signed URLs)  
- [x] Taxon seed + isolation + viewer cannot create  

---

## 7. Phase 4 — Timeline, Tasks & Dashboard ✅

**Goal:** Daily care loop with baseline watering recommendations.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] Tables: `events`, `tasks`, `task_plants`, `watering_states`
2. [x] Event create/list; plant + household timelines
3. [x] `POST …/water` + baseline engine (factor breakdown, due dates, engine tasks)
4. [x] Task CRUD + complete → event
5. [x] Dashboard aggregate endpoint + UI cards
6. [x] Frontend: timeline, tasks page, dashboard (Today)

### Design note

`watering_states` + explainable baseline calculator in place; Phase 5 deepens weather/learning without UI rewrite.

### Runnable check

- [x] Log water from dashboard; event appears on timeline; task completes

### Tests

- [x] Completing prune task emits pruned event  
- [x] Watering + feedback + dashboard  
- [x] Engine unit tests (pot size / season)  

---

## 8. Phase 5 — Watering Engine v1 ✅ (baseline + weather)

**Goal:** Product differentiator.

**Status:** Baseline + Open-Meteo weather factors complete (2026-07-20). Further learning/sensor work remains post-v0.1.

### Tasks

1. Domain module: pure functions for factors, moisture score, due date, confidence
2. Learning: EMA updates on feedback
3. Persist `watering_states`, `watering_feedback`
4. Recompute on plant change, water log, feedback, nightly job
5. Engine-generated tasks with `source_key` upsert
6. API: recommendation, due list, pause, override, feedback
7. UI: factor breakdown, confidence, watering run mode
8. Unit tests with golden scenarios (winter indoor, outdoor after rain mock, small terracotta pot, etc.)

### Runnable check

- Two identical species plants with different pot sizes get different due dates  
- Feedback “too wet” lengthens interval bias  
- UI explains why  

### Tests

- Extensive domain unit tests (this is the crown jewel)  
- Recompute idempotency  

---

## 9. Phase 6 — Weather (Open-Meteo) ✅

**Goal:** Automatic environmental adjustment.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] `weather_cache` table + httpx Open-Meteo client
2. [x] Household coordinates in settings UI
3. [x] Dashboard weather card + refresh
4. [x] Engine factors: humidity, temp, precip (especially outdoor)
5. [x] Graceful degrade when offline / no coords

### Runnable check

- [x] Set lat/lon → weather card; outdoor rain lengthens interval (unit + mocked tests)

### Tests

- [x] Mocked Open-Meteo refresh  
- [x] Engine outdoor + rain fixture  

---

## 10. Phase 7 — Layout Designer ✅

**Goal:** Spatial mental model.

**Status:** Complete (2026-07-20) — HTML5 drag canvas + list assign; full dnd-kit polish later.

### Tasks

1. [x] Tables: `sites`, `spaces`, `containers`, `placements`
2. [x] Full layout API
3. [x] Frontend canvas + assign list
4. [ ] Placement path on plant cards (next polish)
5. [ ] Watering run order by layout (next polish)
6. [x] Relocate events on move

### Runnable check

- [x] Create rooms, place/drag plants, persists  
- [x] Unassigned list assign works  

### Tests

- [x] Placement + tree API  

---

## 11. Phase 8 — Calendar, QR Labels, Statistics ✅

**Goal:** Completeness for daily/weekly planning and physical labels.

**Status:** Complete (2026-07-20)

### Tasks

1. [x] Calendar API + month UI  
2. [x] QR + PDF label generation (single + batch)  
3. [x] Stats summary API + stats page  
4. [ ] Optional iCal token feed (later)  

### Runnable check

- [x] PDF label downloads  
- [x] Stats show survival and water estimates  
- [x] Calendar shows tasks/events  

### Tests

- [x] PDF bytes start with %PDF  
- [x] Stats + layout + weather tests  

---

## 12. Phase 9 — Plant Identification

**Goal:** Optional PlantNet.

### Tasks

1. `identification_jobs` + adapter  
2. Settings for API key (env + household override)  
3. UI flow: identify → pick candidate → apply taxon  
4. Store identification event  

### Runnable check

- With key: identify returns candidates  
- Without key: clear configuration message  

### Tests

- Mock PlantNet responses  

---

## 13. Phase 10 — Polish & v0.1 Release

**Goal:** Something people can self-host seriously.

### Tasks

1. PWA manifest + basic offline shell  
2. Accessibility pass (keyboard, focus, contrast)  
3. Backup docs + `scripts/backup.sh` example  
4. Arm64 image build  
5. Rate limiting on auth  
6. Security headers example (Caddyfile)  
7. CONTRIBUTING, SECURITY, screenshots  
8. Tag `v0.1.0`  

### Exit criteria = SPEC §11 Acceptance Criteria

---

## 14. Post-v0.1 Backlog (ordered by value)

| Item | Why later |
|------|-----------|
| Inventory (fertilizer/tools) | Useful but not care-critical |
| Webhooks + plugin runtime | Integrators after API stable |
| OIDC / proxy auth | Power self-hosters |
| Local AI identification | Hardware-dependent |
| Sensor integrations | Niche |
| iCal write-back / two-way sync | Complexity |
| Full i18n locales | After English UX solid |
| Data export ZIP | Portability |
| Multi-plant bulk edit | Power users |
| Notification channels (email/ntfy/Gotify) | High value — candidate for **v0.2** |
| Read-only plant-sitter links | Trust model careful design |

### Explicitly not planned

- Built-in group chat  
- Cryptocurrency / NFT plants  
- Forced cloud accounts  
- Telemetry without opt-in  

---

## 15. Suggested PR / Commit Cadence

Each bullet can be 1–3 PRs; keep main deployable.

```
Phase 1
  ├─ chore: monorepo scaffold
  ├─ chore: docker compose postgres + api
  └─ feat: frontend shell + dark mode

Phase 2
  ├─ feat: users auth jwt
  ├─ feat: households memberships
  └─ feat: setup wizard ui

Phase 3
  ├─ feat: taxa seed + plants api
  ├─ feat: plant ui list detail
  └─ feat: photo uploads

Phase 4
  ├─ feat: events timeline
  ├─ feat: tasks
  └─ feat: dashboard

Phase 5
  ├─ feat: watering engine domain
  ├─ feat: watering api + states
  └─ feat: watering ui + feedback

Phase 6
  ├─ feat: open-meteo weather
  └─ feat: weather engine factors

Phase 7
  ├─ feat: layout schema api
  └─ feat: layout designer ui

Phase 8
  ├─ feat: calendar
  ├─ feat: qr labels
  └─ feat: statistics

Phase 9
  └─ feat: plantnet identify

Phase 10
  └─ release: v0.1.0 hardening
```

---

## 16. Risk Schedule

| Phase | Risk | Mitigation |
|-------|------|------------|
| 2 | Auth cookie CSRF footguns | Document dual mode; test both |
| 3 | Photo storage disk fill | Quotas + compression |
| 5 | Engine distrust | Explainability UI + overrides |
| 6 | Geo privacy concerns | Document; local only |
| 7 | DnD a11y | List editor fallback |
| 9 | PlantNet ToS/keys | Optional feature flag |

---

## 17. Immediate Next Step

**Start Phase 1** after design docs are accepted:

1. Scaffold `backend/` and `frontend/`  
2. Docker Compose with Postgres + API health  
3. Minimal README “quick start”  
4. Keep docs in repo root as living design  

No feature work before the stack boots cleanly.

---

## 18. Versioning

| Version | Meaning |
|---------|---------|
| `0.x` | Pre-stable; breaking API allowed with changelog |
| `0.1.0` | First self-host recommendation |
| `1.0.0` | Stable API + migrations promise |

---

*This roadmap is the execution order. When reality conflicts with the plan, update this file in the same change that alters sequence — do not leave the roadmap lying.*
