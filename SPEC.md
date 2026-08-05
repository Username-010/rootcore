# RootCore — Product Specification

**Version:** 0.1 (design)  
**Audience:** Engineers, designers, and future contributors  
**Related:** [PROJECT_PLAN.md](./PROJECT_PLAN.md) · [DATABASE.md](./DATABASE.md) · [API.md](./API.md) · [ROADMAP.md](./ROADMAP.md)

---

## 1. Product Overview

### 1.1 One-sentence pitch

RootCore is a self-hosted plant care platform that combines collection management with an adaptive watering engine, spatial layouts, and household collaboration.

### 1.2 Goals

1. Make daily plant care (especially watering) **smarter and less guesswork**.
2. Give multi-person households **shared ownership** of a collection without chaos.
3. Provide a **beautiful, fast, accessible** interface that works on phone and desktop.
4. Remain **fully self-hosted**, Docker-first, privacy-respecting, and API-open.
5. Be a realistic **alternative to HortusFox** for users who care more about care intelligence than chat themes.

### 1.3 Non-goals (v1)

- Social network, public plant feeds, marketplace
- Built-in group chat
- Full retail/inventory ERP for nurseries
- Native iOS/Android apps (responsive PWA-ready web first)
- Guaranteed botanical authority (we cache care defaults; users can override)
- Medical/agricultural certification or commercial grower compliance

---

## 2. Personas

### 2.1 Alex — Houseplant collector

- 40–200 indoor plants across rooms and shelves  
- Wants photos, scientific names, and “what needs me today”  
- Frustrated by fixed watering schedules that ignore winter  

**Primary jobs:** Dashboard, watering list, plant detail, photos  

### 2.2 Sam & Jordan — Shared household

- Couples or roommates sharing plant care  
- Need to see who watered what; avoid double-watering  
- One person may be “plant lead,” other helps on weekends  

**Primary jobs:** Household membership, task assignment, timeline  

### 2.3 Riley — Balcony / outdoor gardener

- Mix of pots and beds; weather-sensitive  
- Wants outdoor plants to skip watering after rain  

**Primary jobs:** Weather-aware watering, outdoor layout  

### 2.4 Morgan — Self-host admin

- Runs Docker on NAS / mini PC  
- Cares about backups, reverse proxy, no phone-home  
- May integrate via API  

**Primary jobs:** Install, env config, API tokens, health  

### 2.5 Casey — Greenhouse hobbyist (secondary)

- Rooms + greenhouse; propagation and repotting tasks  
- Layout designer and QR labels high value  

---

## 3. Information Architecture

### 3.1 Global navigation (authenticated)

| Nav item | Purpose |
|----------|---------|
| **Dashboard** | Today’s focus |
| **Plants** | Collection browse/search |
| **Tasks** | All care tasks & filters |
| **Calendar** | Month/week of tasks & events |
| **Layout** | Spatial designer |
| **Timeline** | Household activity feed |
| **Stats** | Analytics |
| **Settings** | Household, members, integrations, profile |

Mobile: bottom nav for Dashboard / Plants / Tasks / More.

### 3.2 Household context

- Header switcher when user has multiple households  
- All data views scoped to active household  
- Create / invite under Settings → Household  

### 3.3 Plant detail tabs

1. **Overview** — status, location path, next water, quick actions  
2. **Care** — watering recommendation breakdown, soil/pot, schedule overrides  
3. **Timeline** — events  
4. **Photos** — gallery  
5. **Tasks** — open/closed for this plant  
6. **Notes** — freeform markdown-ish notes (stored as note events or dedicated field)

---

## 4. Functional Requirements

Requirements use MoSCoW: **M**ust / **S**hould / **C**ould / **W**on’t (v1).

### 4.1 Authentication & users

| ID | Priority | Requirement |
|----|----------|-------------|
| AUTH-1 | M | Email + password registration (can be disabled by admin env for invite-only) |
| AUTH-2 | M | Login issues JWT access + refresh; logout revokes refresh |
| AUTH-3 | M | Password change when authenticated |
| AUTH-4 | S | Password reset via email when SMTP configured |
| AUTH-5 | S | First-run setup wizard when no users exist (create owner) |
| AUTH-6 | C | OIDC / reverse-proxy auth |
| AUTH-7 | M | Profile: display name, preferred units (metric/imperial), theme, timezone |

**Design note:** Invite-only mode (`REGISTRATION_MODE=open|invite|closed`) is better for self-hosted family servers than public signup.

### 4.2 Households & permissions

| ID | Priority | Requirement |
|----|----------|-------------|
| HH-1 | M | User can create a household (becomes owner) |
| HH-2 | M | Owner/admin can invite by email or invite link |
| HH-3 | M | Roles: owner, admin, member, viewer |
| HH-4 | M | Permission matrix enforced server-side |
| HH-5 | M | Transfer ownership; prevent removing last owner |
| HH-6 | S | Per-member notification preferences |
| HH-7 | C | Guest plant-sitter time-boxed access |

#### Permission matrix (v1)

| Action | Owner | Admin | Member | Viewer |
|--------|-------|-------|--------|--------|
| View plants/tasks/layout | ✓ | ✓ | ✓ | ✓ |
| Create/edit plants | ✓ | ✓ | ✓ | |
| Log watering / complete tasks | ✓ | ✓ | ✓ | |
| Delete plants | ✓ | ✓ | * | |
| Manage layout | ✓ | ✓ | ✓ | |
| Manage members | ✓ | ✓ | | |
| Household settings / delete | ✓ | | | |
| Integrations API keys (PlantNet) | ✓ | ✓ | | |

\* Members delete only plants they created, or household setting allows any member delete.

### 4.3 Taxonomy (species & cultivars)

| ID | Priority | Requirement |
|----|----------|-------------|
| TAX-1 | M | Species records: scientific name, common names[], family optional |
| TAX-2 | M | Cultivar/variety under species |
| TAX-3 | M | Care profile defaults: moisture preference, light, drought tolerance, baseline water interval range, fertilize season notes |
| TAX-4 | S | Seed DB of common houseplants for autocomplete |
| TAX-5 | S | User-custom species when not in catalog (household-scoped custom taxa) |
| TAX-6 | C | GBIF / external enrichment |

**Design decision:** Catalog is **global read-mostly** + **household custom taxa**. Plants point at `taxon_id` (species or cultivar). This is better than free-text-only scientific names (inconsistent) or a rigid global-only list (missing rare plants).

### 4.4 Plants (specimens)

| ID | Priority | Requirement |
|----|----------|-------------|
| PL-1 | M | Unlimited plants per household |
| PL-2 | M | Fields: nickname, taxon, acquired_at, status (active/dormant/deceased/archived), environment (indoor/outdoor/greenhouse), pot size L, pot material, soil type, location placement optional, notes, estimated value optional |
| PL-3 | M | Soft archive / mark deceased (with date & reason) — retain history |
| PL-4 | M | Search by name, species, tags, room |
| PL-5 | M | Tags (household-scoped freeform) |
| PL-6 | S | Parent/child for propagation lineage |
| PL-7 | S | Custom attributes (key/value) without schema migrations |
| PL-8 | M | Cover photo |

**Status model:**

- `active` — in care rotation  
- `dormant` — reduced care (winter bulbs, etc.)  
- `deceased` — kept for survival stats  
- `archived` — given away / removed from active UI  

### 4.5 Photos

| ID | Priority | Requirement |
|----|----------|-------------|
| PH-1 | M | Unlimited photos per plant (storage quotas configurable) |
| PH-2 | M | Upload jpeg/png/webp; server generates thumb + display sizes |
| PH-3 | M | Caption, taken_at, set as cover |
| PH-4 | M | Auth-gated download URLs |
| PH-5 | S | Bulk upload |
| PH-6 | C | EXIF orientation & date extraction |

### 4.6 Timeline / history

| ID | Priority | Requirement |
|----|----------|-------------|
| TL-1 | M | Append events for care actions and system notes |
| TL-2 | M | Plant timeline and household timeline views |
| TL-3 | M | Event types: watered, fertilized, pruned, repotted, propagated, harvested, cleaned, relocated, note, photo, health, identified, custom |
| TL-4 | M | Events store actor, timestamp, payload JSON, optional media |
| TL-5 | S | Edit/delete own events within time window (admin any) — not silent rewrite; prefer correct + audit |
| TL-6 | S | Filters by type / plant / actor |

### 4.7 Watering engine

| ID | Priority | Requirement |
|----|----------|-------------|
| WE-1 | M | Never rely solely on fixed “every N days” as the only model |
| WE-2 | M | Compute `next_water_due_at`, `urgency`, `recommended_amount`, `confidence`, `factor_breakdown[]` |
| WE-3 | M | Factors: species baseline, pot size, soil, age/stage, season, indoor/outdoor, last watering, weather, humidity, user feedback bias |
| WE-4 | M | Log watering creates timeline event and triggers recompute |
| WE-5 | M | User feedback: too_dry / ok / too_wet updates per-plant learning biases |
| WE-6 | M | Manual override: snooze / water on date / pause recommendations |
| WE-7 | S | “Watering run” mode: sorted route by layout space order |
| WE-8 | S | Volume estimate (ml) from pot size for stats |
| WE-9 | C | Soil moisture sensor integration via plugin |

**UX for recommendation:**

```
Next water: Tomorrow · Normal soak
Confidence: Medium (12 waterings logged)

Why:
• Baseline for Monstera deliciosa: ~7 days
• Small pot (−15%)
• Low indoor humidity (+10% demand)
• Your feedback history: slightly longer intervals
```

Transparency builds trust; HortusFox-style silent reminders do not.

### 4.8 Tasks

| ID | Priority | Requirement |
|----|----------|-------------|
| TK-1 | M | Task types: water, prune, repot, propagate, harvest, clean, fertilize, custom |
| TK-2 | M | Tasks link to 0..n plants (0 = household chore) |
| TK-3 | M | Due date/time, priority, assignee optional, status |
| TK-4 | M | Completing care tasks can auto-emit timeline events |
| TK-5 | M | Engine-generated watering tasks (deduped, regenerable) |
| TK-6 | S | Recurring custom reminders (RRULE or simple interval) for non-water tasks |
| TK-7 | S | Batch complete |

**Design decision:** Watering *recommendations* are engine output; *tasks* are the actionable queue. Generated watering tasks are marked `source=engine` and update when engine recomputes (not infinite stale copies).

### 4.9 Calendar

| ID | Priority | Requirement |
|----|----------|-------------|
| CAL-1 | M | Month view of tasks due + key events |
| CAL-2 | S | Week view |
| CAL-3 | S | iCal export URL (tokenized) for external calendars |

### 4.10 Weather

| ID | Priority | Requirement |
|----|----------|-------------|
| WX-1 | M | Household or site lat/lon (+ timezone) |
| WX-2 | M | Fetch Open-Meteo forecast; cache aggressively |
| WX-3 | M | Feed temp, humidity, precipitation into watering engine |
| WX-4 | M | Dashboard weather card |
| WX-5 | S | Per-site coordinates (cabin vs home) |
| WX-6 | C | Historical weather for growth correlation |

### 4.11 Plant identification

| ID | Priority | Requirement |
|----|----------|-------------|
| ID-1 | M | Upload photo → PlantNet → ranked candidates |
| ID-2 | M | Apply candidate to create/update taxon on plant |
| ID-3 | M | Store identification event with raw response (privacy: household only) |
| ID-4 | S | Admin-configured API key; clear error if missing |
| ID-5 | C | Local AI identifier plugin |

### 4.12 Layout designer

| ID | Priority | Requirement |
|----|----------|-------------|
| LO-1 | M | CRUD sites → spaces → containers |
| LO-2 | M | Place plants on space canvas with x,y |
| LO-3 | M | Drag-and-drop reposition; snap optional |
| LO-4 | M | List unassigned plants; assign via drop or form |
| LO-5 | S | Space templates (e.g., “standard shelf 5 slots”) |
| LO-6 | S | Mobile: list + simple reorder before full canvas |
| LO-7 | C | Photo background for room plan |

**UX note:** On small screens, a **structured list** (room → shelf → plants) is more useful than pixel canvas. Canvas is desktop-primary; list editor is mobile-primary. Both edit the same model.

### 4.13 QR labels

| ID | Priority | Requirement |
|----|----------|-------------|
| QR-1 | M | Generate QR encoding deep link `/p/{plant_id}` or public token URL |
| QR-2 | M | Printable label: name, species, QR; sheet layout (A4/Letter) |
| QR-3 | S | Batch select plants → PDF download |
| QR-4 | S | Optional private token so QR doesn’t expose UUID guessing (still requires auth unless public view enabled) |

**Security:** Default QR opens app login then plant. Optional `public_plant_cards` household setting for read-only care card without full account (off by default).

### 4.14 Statistics

| ID | Priority | Requirement |
|----|----------|-------------|
| ST-1 | M | Collection size, active vs deceased, survival rate |
| ST-2 | M | Task completion rate (7/30/90d) |
| ST-3 | M | Water usage estimate over time |
| ST-4 | S | Collection estimated value sum |
| ST-5 | S | Plants by room / species distribution |
| ST-6 | S | Growth history via photo timeline (qualitative) |
| ST-7 | C | Health score aggregate |

### 4.15 Dashboard

| ID | Priority | Requirement |
|----|----------|-------------|
| DB-1 | M | Today’s tasks |
| DB-2 | M | Plants needing attention (overdue water, failed health) |
| DB-3 | M | Weather summary |
| DB-4 | M | Upcoming reminders (7 days) |
| DB-5 | M | Quick actions: add plant, log water, add task |
| DB-6 | S | “Watering run” start button |
| DB-7 | S | Recent household activity |

### 4.16 Search

| ID | Priority | Requirement |
|----|----------|-------------|
| SE-1 | M | Global search plants by nickname, species, tags |
| SE-2 | S | Search tasks and timeline notes |
| SE-3 | C | Postgres full-text ranking |

---

## 5. Non-Functional Requirements

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-1 | M | Responsive: 320px–4K usable |
| NFR-2 | M | Dark mode + light mode |
| NFR-3 | M | WCAG 2.2 AA for core flows (login, dashboard, water, plant detail) |
| NFR-4 | M | API documented via OpenAPI 3 (Swagger UI at `/api/docs`) |
| NFR-5 | M | Docker Compose one-command deploy |
| NFR-6 | M | Time-to-interactive dashboard < 2s on LAN for 500 plants (target) |
| NFR-7 | M | No mandatory external accounts for core features (weather included) |
| NFR-8 | M | PlantNet optional |
| NFR-9 | S | PWA installable (manifest + service worker caching shell) |
| NFR-10 | M | Accessible color contrast for urgency (not color-only: icons + text) |
| NFR-11 | M | Backup documentation for DB + media volume |
| NFR-12 | S | Multi-arch images (amd64, arm64) for Pi/NAS |

---

## 6. UX Principles

1. **Care loop first** — Opening the app should answer: “What do my plants need today?”  
2. **Explain recommendations** — Never black-box watering.  
3. **Fast complete** — Logging water is ≤ 2 taps from dashboard.  
4. **Honest empty states** — Guide first plant, first room, first water.  
5. **Progressive complexity** — Advanced factors collapsed by default.  
6. **Household-aware copy** — “Jordan watered Monstera · 2h ago”.  
7. **Destructive actions confirmed** — archive/delete plant, leave household.  
8. **Offline-tolerant later** — v1 online-only; design mutations idempotent for future offline queue.

### 6.1 Visual direction

- Calm botanical aesthetic without kitsch clipart overload  
- shadcn neutrals + one green accent (user-overridable)  
- Large plant cover imagery in cards  
- Urgency: muted amber (due soon), rose (overdue), emerald (ok) — with labels  

### 6.2 Key user journeys

#### J1 — First run

1. Compose up → open URL  
2. Setup wizard: admin account, household name, location for weather  
3. Optional: add first room  
4. Add first plant (name + species autocomplete)  
5. Land on dashboard with “Log first watering” CTA  

#### J2 — Morning watering

1. Open dashboard  
2. See 6 plants due  
3. Start watering run  
4. For each: confirm water / skip / snooze  
5. Feedback prompt occasionally: “How was moisture?”  

#### J3 — New plant from photo

1. Add plant → Identify  
2. Pick PlantNet candidate  
3. Set pot size & room  
4. Engine produces initial recommendation (low confidence)  

#### J4 — Invite partner

1. Settings → Members → Invite link  
2. Partner joins as member  
3. Both see shared tasks; completions attributed  

---

## 7. Content & Internationalization

- UI strings in English for v1  
- All user-facing strings via i18n keys (no hardcoded dead-ends)  
- Dates/times in user timezone  
- Units: ml/L vs oz/gal toggle  

---

## 8. Privacy & Ethics

- Self-hosted: data stays on user’s server  
- No analytics by default  
- PlantNet images sent only when user invokes identify  
- Weather queries by lat/lon (document that Open-Meteo sees coordinates)  
- GDPR-ish export: household data export JSON/ZIP (Should)  

---

## 9. Admin & Configuration

Environment-driven (see `.env.example` at scaffold):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres |
| `SECRET_KEY` | Token signing |
| `REGISTRATION_MODE` | open / invite / closed |
| `MEDIA_ROOT` | File path |
| `SMTP_*` | Optional mail |
| `PLANTNET_API_KEY` | Optional global key (households may override) |
| `CORS_ORIGINS` | Frontend origins |
| `PUBLIC_BASE_URL` | Links in QR / invites |

In-app admin (owner): household settings, members, integration keys, danger zone.

**Instance-level superadmin** (optional env-created user): manage all households on multi-tenant public instances. For pure family self-host, single household is enough — still model instance admin for correctness.

---

## 10. Error & Edge Cases

| Case | Behavior |
|------|----------|
| Weather fetch fails | Engine uses last cache or season-only modifiers; show banner |
| PlantNet key missing | Identify button explains configuration |
| Zero plants | Dashboard onboarding checklist |
| Viewer tries to water | 403 + UI hide actions |
| Clock skew / timezone | Store UTC; display local |
| Huge photo upload | Reject over `MAX_UPLOAD_MB` with clear error |
| Duplicate engine tasks | Upsert by (plant_id, type, source=engine) |

---

## 11. Acceptance Criteria (v0.1 release)

A build is “v0.1 usable alternative” when:

1. Docker Compose brings up healthy stack.  
2. Two users in one household can manage plants.  
3. Plants have photos, taxonomy, placement.  
4. Watering engine produces explained due dates that change with weather/feedback.  
5. Tasks + dashboard drive daily care.  
6. OpenAPI documents the API.  
7. Layout list/canvas assigns plants to rooms.  
8. QR PDF generates for a plant.  
9. Basic stats page loads.  
10. Dark mode works; mobile can complete watering.

---

## 12. Open Product Questions (resolved defaults)

| Question | Default decision | Notes |
|----------|------------------|-------|
| License | AGPL-3.0 | See PROJECT_PLAN K10 |
| Public plant pages | Off | Optional later |
| Chat | No | |
| Inventory | Post-v0.1 | |
| Multi-household per user | Yes | |
| Currency for collection value | Household setting | Display-only |
| Deceased plants in survival rate | Yes, explicit formula | documented in stats |

---

*This specification is the product contract. Implementation may refine UX details but must not silently drop Must requirements without updating this document.*
